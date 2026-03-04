# Plan implementacji: File Upload w Homeclaw Chat

## Architektura

```
[Frontend: File Picker / Drag&Drop / Paste]
    ↓ base64 + metadata
[WebSocket: homeclaw/chat/send_stream + attachments[]]
    ↓
[Backend: ws_handlers/chat.py - walidacja + zapis na dysk]
    ↓
[Backend: file_processor.py - ekstrakcja treści]
    ├── images → base64 zachowane do wysłania do AI vision API
    ├── text/* → odczyt treści, dołączenie do query
    └── PDF → PyPDF2: ekstrakcja tekstu → dołączenie do query
    ↓
[Backend: query_processor._build_messages() - multimodal content blocks]
    ↓
[Provider: Gemini → inlineData, OpenAI → image_url, Anthropic → image source]
```

## Obsługiwane typy plików

- **Obrazki**: PNG, JPEG, GIF, WebP → preview w chacie + vision API
- **Tekst**: TXT, CSV, Markdown, HTML, JSON, XML → ekstrakcja treści
- **PDF**: ekstrakcja tekstu (PyPDF2)

## Limity

| Typ | Max rozmiar | Inne limity |
|-----|-------------|-------------|
| Obrazki | 10 MB | max 5 plików na wiadomość |
| Tekst | 5 MB | max 100K znaków po ekstrakcji |
| PDF | 10 MB | max 10 stron |

## Fazy implementacji

### FAZA 1: Typy i interfejsy (backend + frontend)

**Backend - nowy moduł `file_processor.py`:**
```python
@dataclass
class FileAttachment:
    file_id: str          # UUID
    filename: str         # oryginalna nazwa
    mime_type: str        # np. "image/png", "text/plain", "application/pdf"
    size: int             # w bajtach
    storage_path: str     # ścieżka na dysku HA: /config/homeclaw/uploads/{session_id}/{file_id}.ext

ALLOWED_MIME_TYPES = {
    # Obrazki
    "image/png", "image/jpeg", "image/gif", "image/webp",
    # Tekst
    "text/plain", "text/csv", "text/markdown", "text/html",
    "application/json", "application/xml",
    # PDF
    "application/pdf",
}

MAX_FILE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_TEXT_CHARS = 100_000           # 100K znaków
MAX_PDF_PAGES = 10
MAX_ATTACHMENTS_PER_MESSAGE = 5
```

**Backend - `storage.py` Message rozszerzenie:**
- Dodanie pola `attachments: list[dict] = field(default_factory=list)` do dataclass `Message`
- Każdy attachment to dict z `file_id`, `filename`, `mime_type`, `size`, `storage_path`

**Frontend - `types/message.ts` rozszerzenie:**
```typescript
interface FileAttachment {
  file_id: string;
  filename: string;
  mime_type: string;
  size: number;
  data_url?: string;    // "data:image/png;base64,..." dla obrazków (preview)
  content?: string;     // base64 content do wysłania WS
  status: 'pending' | 'uploading' | 'ready' | 'error';
}

interface Message {
  // ... istniejące pola ...
  attachments?: FileAttachment[];
}
```

### FAZA 2: Frontend - UI uploadu plików

**Nowy komponent `AttachButton.svelte`:**
- Przycisk paperclip w `input-footer` obok `ProviderSelector`
- Otwiera natywny file picker z `accept` filtrującym dozwolone typy
- Multi-select enabled

**Nowy komponent `AttachmentPreview.svelte`:**
- Wyświetlany w `input-main` nad textarea (kiedy są pliki)
- Obrazki: miniaturka z remove button (X)
- Tekstowe pliki: chip z ikoną pliku + nazwa + size + remove
- PDF: chip z ikoną PDF + nazwa + remove

**Modyfikacja `MessageInput.svelte`:**
- Obsługa drag & drop (ondragover, ondrop) na textarea wrapper
- Obsługa Ctrl+V paste (onpaste event → clipboard items → image/file)
- Przekazywanie plików do parenta via callback

**Modyfikacja `InputArea.svelte`:**
- State: `let pendingAttachments = $state<FileAttachment[]>([])`
- File processing pipeline: walidacja → odczyt base64 → preview generation
- Przekazanie attachmentów do `sendMessageStream`

**Modyfikacja `MessageBubble.svelte`:**
- Renderowanie attachmentów w wiadomościach użytkownika:
  - Obrazki: `<img>` z base64 data URL (thumbnail)
  - Pliki: chip z ikoną + nazwa + rozmiar

### FAZA 3: Backend - WebSocket + File Processing

**`ws_handlers/chat.py` - rozszerzenie schemy:**
```python
vol.Optional("attachments"): vol.All(
    list,
    vol.Length(max=5),
    [vol.Schema({
        vol.Required("filename"): str,
        vol.Required("mime_type"): str,
        vol.Required("content"): str,  # base64
        vol.Optional("size"): int,
    })]
)
```

**Nowy moduł `file_processor.py` - funkcje:**
1. `validate_attachment()` - sprawdza mime type, rozmiar, base64 validity
2. `save_attachment()` - zapisuje na dysku w `/config/homeclaw/uploads/{session_id}/`
3. `extract_text_content()` - ekstrakcja tekstu:
   - text/* → UTF-8 decode
   - PDF → `PyPDF2` ekstrakcja tekstu
4. `prepare_for_provider()` - przygotowuje dane do wysłania do AI:
   - Obrazki → base64 + mime_type (do multimodal content blocks)
   - Tekst/PDF → wyekstrahowany tekst jako kontekst

**Modyfikacja `ws_handlers/chat.py`:**
- `ws_send_message_stream`: walidacja + zapis attachmentów, przekazanie do `agent.process_query_stream()`
- Message zapisywany z referencjami do plików w `attachments`

### FAZA 4: Provider integration (multimodal)

**`core/query_processor.py` `_build_messages()`:**
- Nowy parametr `attachments`
- Dla wiadomości z obrazkami: `content` staje się listą content blocks zamiast stringa
- Dla wiadomości z plikami tekstowymi: tekst dołączany do query jako kontekst

**Provider-specific conversion - obrazki:**

Gemini (`_gemini_convert.py`):
```python
{"role": "user", "parts": [
    {"text": "opisz ten obraz"},
    {"inlineData": {"mimeType": "image/png", "data": "base64..."}}
]}
```

OpenAI (`openai.py`):
```python
{"role": "user", "content": [
    {"type": "text", "text": "opisz ten obraz"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
]}
```

Anthropic (`anthropic.py`):
```python
{"role": "user", "content": [
    {"type": "text", "text": "opisz ten obraz"},
    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "base64..."}}
]}
```

**Tekst/PDF - wspólne dla wszystkich providerów:**
```python
{"role": "user", "content": f"User message: {query}\n\n---\nAttached file '{filename}':\n{extracted_text}"}
```

### FAZA 5: Serwowanie plików + historia

**Thumbnails w metadata:**
- Przy zapisie obrazka - generować mały base64 thumbnail (~200px) i trzymać w metadata wiadomości
- Pozwala na wyświetlanie preview w historii czatu bez HTTP endpoint
- Pełne obrazki dostępne z dysku gdy potrzeba

**HTTP Endpoint (opcjonalny):**
- HA View do serwowania plików z `/config/homeclaw/uploads/`
- Potrzebny jeśli chcemy wyświetlać pełne obrazki z historii

**`session.service.ts` `selectSession()`:**
- Ładowanie attachmentów z metadata wiadomości
- Thumbnails inline, pełne pliki via HTTP endpoint

## Podsumowanie zmian w plikach

| Warstwa | Plik | Zmiana |
|---------|------|--------|
| **Frontend types** | `types/message.ts` | + `FileAttachment` interface, + `attachments?` w `Message` |
| **Frontend new** | `components/Input/AttachButton.svelte` | Nowy - przycisk attach |
| **Frontend new** | `components/Input/AttachmentPreview.svelte` | Nowy - preview plików |
| **Frontend mod** | `components/Input/InputArea.svelte` | + attachment state, przekazanie do WS |
| **Frontend mod** | `components/Input/MessageInput.svelte` | + drag & drop, paste |
| **Frontend mod** | `components/Chat/MessageBubble.svelte` | + renderowanie attachmentów |
| **Frontend mod** | `services/websocket.service.ts` | + `attachments` w WS params |
| **Backend new** | `file_processor.py` | Nowy - walidacja, zapis, ekstrakcja |
| **Backend mod** | `storage.py` | + `attachments` w `Message` dataclass |
| **Backend mod** | `ws_handlers/_common.py` | + walidacja attachmentów |
| **Backend mod** | `ws_handlers/chat.py` | + attachments w schema, przetwarzanie |
| **Backend mod** | `core/query_processor.py` | + multimodal `_build_messages()` |
| **Backend mod** | `providers/_gemini_convert.py` | + `inlineData` parts |
| **Backend mod** | `providers/openai.py` | + `image_url` content blocks |
| **Backend mod** | `providers/anthropic.py` | + `image` content blocks |
| **Backend dep** | `requirements.txt` | + `PyPDF2` |

## Zależności

- **`PyPDF2`** - czysto Pythonowy, zero natywnych zależności, ekstrakcja tekstu z PDF
