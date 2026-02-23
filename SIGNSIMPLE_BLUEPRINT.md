# SignSimple.io - Complete Technical Blueprint

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SignSimple.io                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────┐     ┌─────────────────────┐       │
│  │  SvelteKit  │────▶│ Cloudflare Edge │────▶│    Turso (libSQL)   │       │
│  │   (Pages)   │     │    (Workers)    │     │   Edge Database     │       │
│  └─────────────┘     └─────────────────┘     └─────────────────────┘       │
│         │                    │                                              │
│         │                    ▼                                              │
│         │            ┌───────────────┐                                      │
│         │            │ Cloudflare R2 │  (Temporary PDF Storage)            │
│         │            └───────────────┘                                      │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    Browser (Client-Side)                         │       │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │       │
│  │  │ Google      │  │  pdf-lib    │  │      PDF.js              │ │       │
│  │  │ Picker API  │  │ (editing)   │  │    (rendering)           │ │       │
│  │  └─────────────┘  └─────────────┘  └──────────────────────────┘ │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  External Services:                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐         │
│  │   Stripe    │  │   Resend    │  │      Google Drive API       │         │
│  │ (payments)  │  │  (email)    │  │  (file storage - drive.file)│         │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Project Structure

```
signsimple/
├── src/
│   ├── app.d.ts                          # SvelteKit type definitions
│   ├── app.html                          # HTML template
│   ├── hooks.server.ts                   # Server hooks (auth, rate limiting)
│   ├── hooks.client.ts                   # Client hooks
│   │
│   ├── lib/
│   │   ├── server/
│   │   │   ├── db/
│   │   │   │   ├── index.ts              # Turso/Drizzle connection
│   │   │   │   ├── schema.ts             # Database schema
│   │   │   │   └── migrations/           # Drizzle migrations
│   │   │   ├── auth/
│   │   │   │   ├── google.ts             # Google OAuth handlers
│   │   │   │   ├── session.ts            # Session management
│   │   │   │   └── middleware.ts         # Auth middleware
│   │   │   ├── services/
│   │   │   │   ├── stripe.ts             # Stripe integration
│   │   │   │   ├── resend.ts             # Email service
│   │   │   │   ├── r2.ts                 # R2 storage operations
│   │   │   │   └── google-drive.ts       # Google Drive API operations
│   │   │   └── utils/
│   │   │       ├── rate-limit.ts         # Rate limiting logic
│   │   │       └── audit.ts              # Audit logging
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                       # Reusable UI components
│   │   │   │   ├── Button.svelte
│   │   │   │   ├── Modal.svelte
│   │   │   │   ├── Input.svelte
│   │   │   │   └── Toast.svelte
│   │   │   ├── pdf/
│   │   │   │   ├── PDFViewer.svelte      # PDF.js rendering component
│   │   │   │   ├── PDFEditor.svelte      # pdf-lib editing interface
│   │   │   │   ├── SignatureField.svelte # Signature placement
│   │   │   │   ├── SignaturePad.svelte   # Drawing signatures
│   │   │   │   └── FieldPlacer.svelte    # Drag-drop field placement
│   │   │   ├── google/
│   │   │   │   ├── GooglePicker.svelte   # Google Picker integration
│   │   │   │   └── DriveFileBrowser.svelte
│   │   │   ├── documents/
│   │   │   │   ├── DocumentCard.svelte
│   │   │   │   ├── DocumentList.svelte
│   │   │   │   └── RecipientForm.svelte
│   │   │   └── layout/
│   │   │       ├── Header.svelte
│   │   │       ├── Sidebar.svelte
│   │   │       └── Footer.svelte
│   │   │
│   │   ├── stores/
│   │   │   ├── auth.ts                   # Auth state store
│   │   │   ├── document.ts               # Current document state
│   │   │   ├── pdf.ts                    # PDF editing state
│   │   │   └── notifications.ts          # Toast notifications
│   │   │
│   │   ├── utils/
│   │   │   ├── pdf-lib-helpers.ts        # pdf-lib utilities
│   │   │   ├── google-picker.ts          # Google Picker utilities
│   │   │   ├── crypto.ts                 # Client-side crypto
│   │   │   └── validation.ts             # Form validation
│   │   │
│   │   └── types/
│   │       ├── document.ts               # Document types
│   │       ├── user.ts                   # User types
│   │       └── google.ts                 # Google API types
│   │
│   └── routes/
│       ├── +layout.svelte                # Root layout
│       ├── +layout.server.ts             # Root layout data
│       ├── +page.svelte                  # Landing page
│       ├── +error.svelte                 # Error page
│       │
│       ├── (auth)/
│       │   ├── login/
│       │   │   └── +page.svelte
│       │   ├── callback/
│       │   │   └── +server.ts            # OAuth callback
│       │   └── logout/
│       │       └── +server.ts
│       │
│       ├── (app)/                        # Protected routes
│       │   ├── +layout.svelte
│       │   ├── +layout.server.ts         # Auth check
│       │   ├── dashboard/
│       │   │   ├── +page.svelte
│       │   │   └── +page.server.ts
│       │   ├── documents/
│       │   │   ├── +page.svelte          # Document list
│       │   │   ├── +page.server.ts
│       │   │   ├── new/
│       │   │   │   ├── +page.svelte      # Create document
│       │   │   │   └── +page.server.ts
│       │   │   └── [id]/
│       │   │       ├── +page.svelte      # View/edit document
│       │   │       ├── +page.server.ts
│       │   │       ├── edit/
│       │   │       │   └── +page.svelte  # PDF editor
│       │   │       └── send/
│       │   │           └── +page.svelte  # Send for signing
│       │   ├── templates/
│       │   │   ├── +page.svelte
│       │   │   └── [id]/
│       │   │       └── +page.svelte
│       │   ├── settings/
│       │   │   ├── +page.svelte
│       │   │   ├── profile/
│       │   │   │   └── +page.svelte
│       │   │   ├── billing/
│       │   │   │   └── +page.svelte
│       │   │   └── integrations/
│       │   │       └── +page.svelte
│       │   └── account/
│       │       └── +page.svelte
│       │
│       ├── sign/
│       │   └── [token]/                  # Public signing page
│       │       ├── +page.svelte
│       │       └── +page.server.ts
│       │
│       └── api/
│           ├── auth/
│           │   ├── google/
│           │   │   └── +server.ts        # Initiate Google OAuth
│           │   └── session/
│           │       └── +server.ts        # Session management
│           ├── documents/
│           │   ├── +server.ts            # CRUD documents
│           │   └── [id]/
│           │       ├── +server.ts
│           │       ├── sign/
│           │       │   └── +server.ts    # Process signature
│           │       └── download/
│           │           └── +server.ts
│           ├── upload/
│           │   ├── presigned/
│           │   │   └── +server.ts        # Get R2 presigned URL
│           │   └── complete/
│           │       └── +server.ts        # Confirm upload
│           ├── google/
│           │   ├── picker-token/
│           │   │   └── +server.ts        # Get picker OAuth token
│           │   └── drive/
│           │       └── +server.ts        # Drive file operations
│           ├── webhooks/
│           │   ├── stripe/
│           │   │   └── +server.ts
│           │   └── resend/
│           │       └── +server.ts
│           └── health/
│               └── +server.ts
│
├── static/
│   ├── favicon.ico
│   ├── robots.txt
│   └── fonts/
│
├── drizzle/
│   └── migrations/                       # Generated migrations
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── .env.example
├── .env.local                            # Local dev (gitignored)
├── .gitignore
├── drizzle.config.ts
├── package.json
├── svelte.config.js
├── tsconfig.json
├── vite.config.ts
├── wrangler.toml
└── README.md
```

---

## 2. Google Picker API Implementation

### 2.1 Google Cloud Console Setup

1. Create a new project in Google Cloud Console
2. Enable these APIs:
   - Google Picker API
   - Google Drive API
3. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized JavaScript origins: `https://signsimple.io`, `http://localhost:5173`
   - Authorized redirect URIs: `https://signsimple.io/callback`, `http://localhost:5173/callback`
4. Create an API Key (for Picker API)

### 2.2 Google Picker Integration Code

#### `src/lib/utils/google-picker.ts`

```typescript
// Google Picker API Utilities
// Uses drive.file scope - non-sensitive, no CASA audit required

import type { GooglePickerConfig, PickerDocument } from '$lib/types/google';

declare global {
  interface Window {
    gapi: typeof gapi;
    google: {
      accounts: {
        oauth2: {
          initTokenClient: (config: any) => any;
        };
      };
      picker: {
        PickerBuilder: new () => any;
        ViewId: {
          DOCS: string;
          PDFS: string;
        };
        Action: {
          PICKED: string;
          CANCEL: string;
        };
        Feature: {
          MULTISELECT_ENABLED: string;
          NAV_HIDDEN: string;
        };
        DocsViewMode: {
          LIST: string;
          GRID: string;
        };
      };
    };
  }
}

const SCOPES = 'https://www.googleapis.com/auth/drive.file';
const DISCOVERY_DOC = 'https://www.googleapis.com/discovery/v1/apis/drive/v3/rest';

let tokenClient: any;
let accessToken: string | null = null;
let pickerInited = false;
let gisInited = false;

/**
 * Load the Google API and Identity Services scripts
 */
export async function loadGoogleScripts(): Promise<void> {
  return new Promise((resolve, reject) => {
    // Load GAPI
    if (!document.getElementById('google-api-script')) {
      const gapiScript = document.createElement('script');
      gapiScript.id = 'google-api-script';
      gapiScript.src = 'https://apis.google.com/js/api.js';
      gapiScript.async = true;
      gapiScript.defer = true;
      gapiScript.onload = () => {
        window.gapi.load('picker', () => {
          pickerInited = true;
          checkAllLoaded();
        });
      };
      gapiScript.onerror = reject;
      document.head.appendChild(gapiScript);
    } else {
      pickerInited = true;
    }

    // Load Google Identity Services
    if (!document.getElementById('google-gis-script')) {
      const gisScript = document.createElement('script');
      gisScript.id = 'google-gis-script';
      gisScript.src = 'https://accounts.google.com/gsi/client';
      gisScript.async = true;
      gisScript.defer = true;
      gisScript.onload = () => {
        gisInited = true;
        checkAllLoaded();
      };
      gisScript.onerror = reject;
      document.head.appendChild(gisScript);
    } else {
      gisInited = true;
    }

    function checkAllLoaded() {
      if (pickerInited && gisInited) {
        resolve();
      }
    }

    // Check if already loaded
    if (window.gapi && window.google?.accounts) {
      resolve();
    }
  });
}

/**
 * Initialize the OAuth token client
 */
export function initTokenClient(clientId: string): void {
  tokenClient = window.google.accounts.oauth2.initTokenClient({
    client_id: clientId,
    scope: SCOPES,
    callback: '', // Will be set in getAccessToken
  });
}

/**
 * Get OAuth access token for Picker
 */
export function getAccessToken(): Promise<string> {
  return new Promise((resolve, reject) => {
    if (accessToken) {
      resolve(accessToken);
      return;
    }

    tokenClient.callback = (response: any) => {
      if (response.error) {
        reject(new Error(response.error));
        return;
      }
      accessToken = response.access_token;
      resolve(accessToken);
    };

    tokenClient.requestAccessToken({ prompt: 'consent' });
  });
}

/**
 * Create and show the Google Picker
 */
export async function showGooglePicker(config: GooglePickerConfig): Promise<PickerDocument[]> {
  const { apiKey, clientId, onSelect, onCancel } = config;

  await loadGoogleScripts();
  initTokenClient(clientId);

  const token = await getAccessToken();

  return new Promise((resolve, reject) => {
    const google = window.google;

    // Create PDF-only view
    const docsView = new google.picker.DocsView(google.picker.ViewId.PDFS)
      .setIncludeFolders(true)
      .setSelectFolderEnabled(false)
      .setMode(google.picker.DocsViewMode.LIST); // Required for drive.file scope

    const picker = new google.picker.PickerBuilder()
      .addView(docsView)
      .setOAuthToken(token)
      .setDeveloperKey(apiKey)
      .setCallback((data: any) => {
        if (data.action === google.picker.Action.PICKED) {
          const documents: PickerDocument[] = data.docs.map((doc: any) => ({
            id: doc.id,
            name: doc.name,
            mimeType: doc.mimeType,
            url: doc.url,
            sizeBytes: doc.sizeBytes,
            lastEditedUtc: doc.lastEditedUtc,
          }));
          onSelect?.(documents);
          resolve(documents);
        } else if (data.action === google.picker.Action.CANCEL) {
          onCancel?.();
          resolve([]);
        }
      })
      .setTitle('Select PDF Document')
      .enableFeature(google.picker.Feature.NAV_HIDDEN)
      .build();

    picker.setVisible(true);
  });
}

/**
 * Download file content from Google Drive using drive.file scope
 * The user must have selected the file via Picker first
 */
export async function downloadDriveFile(
  fileId: string,
  accessToken: string
): Promise<ArrayBuffer> {
  const response = await fetch(
    `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to download file: ${response.statusText}`);
  }

  return response.arrayBuffer();
}

/**
 * Upload file back to Google Drive
 */
export async function uploadToDrive(
  file: Blob,
  fileName: string,
  accessToken: string,
  folderId?: string
): Promise<string> {
  const metadata = {
    name: fileName,
    mimeType: 'application/pdf',
    ...(folderId && { parents: [folderId] }),
  };

  const form = new FormData();
  form.append(
    'metadata',
    new Blob([JSON.stringify(metadata)], { type: 'application/json' })
  );
  form.append('file', file);

  const response = await fetch(
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: form,
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to upload file: ${response.statusText}`);
  }

  const result = await response.json();
  return result.id;
}
```

#### `src/lib/types/google.ts`

```typescript
export interface GooglePickerConfig {
  apiKey: string;
  clientId: string;
  onSelect?: (documents: PickerDocument[]) => void;
  onCancel?: () => void;
}

export interface PickerDocument {
  id: string;
  name: string;
  mimeType: string;
  url: string;
  sizeBytes?: number;
  lastEditedUtc?: number;
}

export interface GoogleDriveFile {
  id: string;
  name: string;
  mimeType: string;
  size: number;
  modifiedTime: string;
  webViewLink: string;
  thumbnailLink?: string;
}
```

#### `src/lib/components/google/GooglePicker.svelte`

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import {
    loadGoogleScripts,
    showGooglePicker,
    downloadDriveFile,
    getAccessToken
  } from '$lib/utils/google-picker';
  import type { PickerDocument } from '$lib/types/google';
  import { PUBLIC_GOOGLE_API_KEY, PUBLIC_GOOGLE_CLIENT_ID } from '$env/static/public';

  export let onFileSelected: (file: ArrayBuffer, fileName: string, driveFileId: string) => void;
  export let disabled = false;

  let isLoading = false;
  let error: string | null = null;

  onMount(async () => {
    try {
      await loadGoogleScripts();
    } catch (e) {
      error = 'Failed to load Google scripts';
      console.error(e);
    }
  });

  async function handlePickerClick() {
    if (disabled || isLoading) return;

    isLoading = true;
    error = null;

    try {
      const documents = await showGooglePicker({
        apiKey: PUBLIC_GOOGLE_API_KEY,
        clientId: PUBLIC_GOOGLE_CLIENT_ID,
      });

      if (documents.length > 0) {
        const doc = documents[0];

        // Verify it's a PDF
        if (doc.mimeType !== 'application/pdf') {
          error = 'Please select a PDF file';
          return;
        }

        // Download the file content
        const token = await getAccessToken();
        const fileContent = await downloadDriveFile(doc.id, token);

        onFileSelected(fileContent, doc.name, doc.id);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to pick file';
      console.error(e);
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="google-picker-container">
  <button
    type="button"
    class="picker-button"
    on:click={handlePickerClick}
    {disabled}
    class:loading={isLoading}
  >
    {#if isLoading}
      <span class="spinner"></span>
      <span>Loading...</span>
    {:else}
      <svg viewBox="0 0 87.3 78" class="drive-icon">
        <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
        <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z" fill="#00ac47"/>
        <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335"/>
        <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
        <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
        <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
      </svg>
      <span>Select from Google Drive</span>
    {/if}
  </button>

  {#if error}
    <p class="error">{error}</p>
  {/if}
</div>

<style>
  .google-picker-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .picker-button {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.5rem;
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .picker-button:hover:not(:disabled) {
    border-color: #4285f4;
    box-shadow: 0 2px 8px rgba(66, 133, 244, 0.2);
  }

  .picker-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .picker-button.loading {
    pointer-events: none;
  }

  .drive-icon {
    width: 24px;
    height: 24px;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #e0e0e0;
    border-top-color: #4285f4;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error {
    color: #d93025;
    font-size: 0.875rem;
    margin: 0;
  }
</style>
```

### 2.3 Loading Selected File into pdf-lib

#### `src/lib/utils/pdf-lib-helpers.ts`

```typescript
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import type { SignatureField, TextField } from '$lib/types/document';

/**
 * Load PDF from ArrayBuffer (from Google Drive or upload)
 */
export async function loadPDF(pdfBytes: ArrayBuffer): Promise<PDFDocument> {
  const pdfDoc = await PDFDocument.load(pdfBytes);
  return pdfDoc;
}

/**
 * Get PDF page count and dimensions
 */
export function getPDFInfo(pdfDoc: PDFDocument) {
  const pages = pdfDoc.getPages();
  return {
    pageCount: pages.length,
    pages: pages.map((page, index) => ({
      index,
      width: page.getWidth(),
      height: page.getHeight(),
    })),
  };
}

/**
 * Add a signature image to PDF
 */
export async function addSignature(
  pdfDoc: PDFDocument,
  signatureImage: Uint8Array,
  field: SignatureField
): Promise<PDFDocument> {
  const pages = pdfDoc.getPages();
  const page = pages[field.pageIndex];

  // Embed the signature image (PNG)
  const image = await pdfDoc.embedPng(signatureImage);

  // Calculate dimensions maintaining aspect ratio
  const aspectRatio = image.width / image.height;
  let drawWidth = field.width;
  let drawHeight = field.width / aspectRatio;

  if (drawHeight > field.height) {
    drawHeight = field.height;
    drawWidth = field.height * aspectRatio;
  }

  // Center the signature in the field
  const x = field.x + (field.width - drawWidth) / 2;
  const y = page.getHeight() - field.y - field.height + (field.height - drawHeight) / 2;

  page.drawImage(image, {
    x,
    y,
    width: drawWidth,
    height: drawHeight,
  });

  return pdfDoc;
}

/**
 * Add text field to PDF
 */
export async function addTextField(
  pdfDoc: PDFDocument,
  field: TextField,
  text: string
): Promise<PDFDocument> {
  const pages = pdfDoc.getPages();
  const page = pages[field.pageIndex];
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);

  const fontSize = field.fontSize || 12;
  const y = page.getHeight() - field.y - fontSize;

  page.drawText(text, {
    x: field.x,
    y,
    size: fontSize,
    font,
    color: rgb(0, 0, 0),
  });

  return pdfDoc;
}

/**
 * Add date stamp to PDF
 */
export async function addDateStamp(
  pdfDoc: PDFDocument,
  field: { pageIndex: number; x: number; y: number },
  date: Date = new Date()
): Promise<PDFDocument> {
  const pages = pdfDoc.getPages();
  const page = pages[field.pageIndex];
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);

  const dateString = date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const y = page.getHeight() - field.y - 12;

  page.drawText(dateString, {
    x: field.x,
    y,
    size: 12,
    font,
    color: rgb(0, 0, 0),
  });

  return pdfDoc;
}

/**
 * Flatten all form fields and annotations
 */
export async function flattenPDF(pdfDoc: PDFDocument): Promise<PDFDocument> {
  const form = pdfDoc.getForm();
  form.flatten();
  return pdfDoc;
}

/**
 * Save PDF to bytes
 */
export async function savePDF(pdfDoc: PDFDocument): Promise<Uint8Array> {
  return pdfDoc.save();
}

/**
 * Create a new blank PDF
 */
export async function createBlankPDF(
  width = 612,
  height = 792
): Promise<PDFDocument> {
  const pdfDoc = await PDFDocument.create();
  pdfDoc.addPage([width, height]);
  return pdfDoc;
}

/**
 * Merge multiple PDFs into one
 */
export async function mergePDFs(pdfDocs: PDFDocument[]): Promise<PDFDocument> {
  const mergedDoc = await PDFDocument.create();

  for (const doc of pdfDocs) {
    const copiedPages = await mergedDoc.copyPages(doc, doc.getPageIndices());
    copiedPages.forEach((page) => mergedDoc.addPage(page));
  }

  return mergedDoc;
}

/**
 * Extract specific pages from PDF
 */
export async function extractPages(
  pdfDoc: PDFDocument,
  pageIndices: number[]
): Promise<PDFDocument> {
  const newDoc = await PDFDocument.create();
  const copiedPages = await newDoc.copyPages(pdfDoc, pageIndices);
  copiedPages.forEach((page) => newDoc.addPage(page));
  return newDoc;
}
```

---

## 3. Drizzle + Turso Database Schema

#### `src/lib/server/db/schema.ts`

```typescript
import { sql } from 'drizzle-orm';
import {
  sqliteTable,
  text,
  integer,
  real,
  blob,
  index,
  uniqueIndex
} from 'drizzle-orm/sqlite-core';

// ============================================
// USERS
// ============================================

export const users = sqliteTable('users', {
  id: text('id').primaryKey(), // UUID
  email: text('email').notNull().unique(),
  name: text('name'),
  avatarUrl: text('avatar_url'),

  // Google OAuth
  googleId: text('google_id').unique(),
  googleAccessToken: text('google_access_token'),
  googleRefreshToken: text('google_refresh_token'),
  googleTokenExpiry: integer('google_token_expiry'), // Unix timestamp

  // Subscription
  stripeCustomerId: text('stripe_customer_id'),
  subscriptionId: text('subscription_id'),
  subscriptionStatus: text('subscription_status', {
    enum: ['active', 'canceled', 'past_due', 'trialing', 'incomplete']
  }),
  subscriptionPlan: text('subscription_plan', {
    enum: ['free', 'starter', 'pro', 'enterprise']
  }).default('free'),
  subscriptionEndDate: integer('subscription_end_date'), // Unix timestamp

  // Usage limits (reset monthly)
  monthlyDocumentsUsed: integer('monthly_documents_used').default(0),
  monthlySignaturesUsed: integer('monthly_signatures_used').default(0),
  usageResetDate: integer('usage_reset_date'), // Unix timestamp

  // Settings
  defaultSignature: blob('default_signature'), // Base64 encoded signature image
  timezone: text('timezone').default('America/New_York'),
  emailNotifications: integer('email_notifications', { mode: 'boolean' }).default(true),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  emailIdx: index('users_email_idx').on(table.email),
  googleIdIdx: index('users_google_id_idx').on(table.googleId),
  stripeCustomerIdx: index('users_stripe_customer_idx').on(table.stripeCustomerId),
}));

// ============================================
// DOCUMENTS
// ============================================

export const documents = sqliteTable('documents', {
  id: text('id').primaryKey(), // UUID
  userId: text('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),

  title: text('title').notNull(),
  description: text('description'),
  status: text('status', {
    enum: ['draft', 'pending', 'completed', 'expired', 'canceled']
  }).default('draft').notNull(),

  // File storage
  storageType: text('storage_type', { enum: ['r2', 'google_drive'] }).notNull(),
  storageId: text('storage_id').notNull(), // R2 key or Google Drive file ID
  originalFileName: text('original_file_name').notNull(),
  fileSize: integer('file_size').notNull(), // bytes
  pageCount: integer('page_count').notNull(),

  // Signed version (after all signatures collected)
  signedStorageId: text('signed_storage_id'),
  signedAt: integer('signed_at', { mode: 'timestamp' }),

  // Template
  isTemplate: integer('is_template', { mode: 'boolean' }).default(false),
  templateId: text('template_id').references(() => documents.id),

  // Expiration
  expiresAt: integer('expires_at', { mode: 'timestamp' }),
  reminderSentAt: integer('reminder_sent_at', { mode: 'timestamp' }),

  // Metadata
  metadata: text('metadata', { mode: 'json' }).$type<Record<string, any>>(),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  userIdIdx: index('documents_user_id_idx').on(table.userId),
  statusIdx: index('documents_status_idx').on(table.status),
  createdAtIdx: index('documents_created_at_idx').on(table.createdAt),
  templateIdx: index('documents_template_idx').on(table.isTemplate),
}));

// ============================================
// DOCUMENT FIELDS (Signature/Text/Date placements)
// ============================================

export const documentFields = sqliteTable('document_fields', {
  id: text('id').primaryKey(), // UUID
  documentId: text('document_id').notNull().references(() => documents.id, { onDelete: 'cascade' }),
  recipientId: text('recipient_id').references(() => recipients.id, { onDelete: 'cascade' }),

  type: text('type', {
    enum: ['signature', 'initial', 'text', 'date', 'checkbox']
  }).notNull(),

  // Position on PDF
  pageIndex: integer('page_index').notNull(),
  x: real('x').notNull(),
  y: real('y').notNull(),
  width: real('width').notNull(),
  height: real('height').notNull(),

  // Field properties
  label: text('label'),
  placeholder: text('placeholder'),
  required: integer('required', { mode: 'boolean' }).default(true),
  fontSize: integer('font_size').default(12),

  // Filled value
  value: text('value'),
  filledAt: integer('filled_at', { mode: 'timestamp' }),
  filledByIp: text('filled_by_ip'),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  documentIdIdx: index('document_fields_document_id_idx').on(table.documentId),
  recipientIdIdx: index('document_fields_recipient_id_idx').on(table.recipientId),
}));

// ============================================
// RECIPIENTS (Signers)
// ============================================

export const recipients = sqliteTable('recipients', {
  id: text('id').primaryKey(), // UUID
  documentId: text('document_id').notNull().references(() => documents.id, { onDelete: 'cascade' }),

  email: text('email').notNull(),
  name: text('name'),
  role: text('role', {
    enum: ['signer', 'viewer', 'approver']
  }).default('signer'),

  // Signing order (1, 2, 3... for sequential signing)
  signingOrder: integer('signing_order').default(1),

  // Status
  status: text('status', {
    enum: ['pending', 'sent', 'viewed', 'signed', 'declined']
  }).default('pending'),

  // Secure access token
  accessToken: text('access_token').notNull().unique(),
  tokenExpiresAt: integer('token_expires_at', { mode: 'timestamp' }),

  // Signing metadata
  viewedAt: integer('viewed_at', { mode: 'timestamp' }),
  signedAt: integer('signed_at', { mode: 'timestamp' }),
  declinedAt: integer('declined_at', { mode: 'timestamp' }),
  declineReason: text('decline_reason'),

  // Verification
  signingIp: text('signing_ip'),
  userAgent: text('user_agent'),

  // Email tracking
  lastEmailSentAt: integer('last_email_sent_at', { mode: 'timestamp' }),
  emailSentCount: integer('email_sent_count').default(0),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  documentIdIdx: index('recipients_document_id_idx').on(table.documentId),
  emailIdx: index('recipients_email_idx').on(table.email),
  accessTokenIdx: uniqueIndex('recipients_access_token_idx').on(table.accessToken),
  statusIdx: index('recipients_status_idx').on(table.status),
}));

// ============================================
// AUDIT LOGS (Immutable)
// ============================================

export const auditLogs = sqliteTable('audit_logs', {
  id: text('id').primaryKey(), // UUID
  documentId: text('document_id').references(() => documents.id, { onDelete: 'set null' }),
  userId: text('user_id').references(() => users.id, { onDelete: 'set null' }),
  recipientId: text('recipient_id').references(() => recipients.id, { onDelete: 'set null' }),

  action: text('action', {
    enum: [
      'document_created',
      'document_updated',
      'document_deleted',
      'document_sent',
      'document_viewed',
      'document_signed',
      'document_declined',
      'document_completed',
      'document_expired',
      'document_downloaded',
      'recipient_added',
      'recipient_removed',
      'reminder_sent',
      'field_added',
      'field_updated',
      'field_filled',
    ]
  }).notNull(),

  // IP and location
  ipAddress: text('ip_address'),
  userAgent: text('user_agent'),
  geoLocation: text('geo_location'),

  // Additional data
  metadata: text('metadata', { mode: 'json' }).$type<Record<string, any>>(),

  // Hash for integrity (SHA-256 of previous log + this log data)
  previousLogHash: text('previous_log_hash'),
  logHash: text('log_hash').notNull(),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  documentIdIdx: index('audit_logs_document_id_idx').on(table.documentId),
  userIdIdx: index('audit_logs_user_id_idx').on(table.userId),
  actionIdx: index('audit_logs_action_idx').on(table.action),
  createdAtIdx: index('audit_logs_created_at_idx').on(table.createdAt),
}));

// ============================================
// TEMPLATES (Reusable document configurations)
// ============================================

export const templates = sqliteTable('templates', {
  id: text('id').primaryKey(), // UUID
  userId: text('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),

  name: text('name').notNull(),
  description: text('description'),
  category: text('category'),

  // Source document
  sourceDocumentId: text('source_document_id').references(() => documents.id),
  storageId: text('storage_id').notNull(), // R2 key

  // Pre-defined fields (JSON array of field definitions)
  fieldDefinitions: text('field_definitions', { mode: 'json' }).$type<Array<{
    type: 'signature' | 'initial' | 'text' | 'date' | 'checkbox';
    pageIndex: number;
    x: number;
    y: number;
    width: number;
    height: number;
    label?: string;
    required: boolean;
    recipientRole?: string;
  }>>(),

  // Pre-defined recipients (roles)
  recipientRoles: text('recipient_roles', { mode: 'json' }).$type<Array<{
    role: string;
    signingOrder: number;
  }>>(),

  // Usage stats
  usageCount: integer('usage_count').default(0),

  isPublic: integer('is_public', { mode: 'boolean' }).default(false),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  userIdIdx: index('templates_user_id_idx').on(table.userId),
  categoryIdx: index('templates_category_idx').on(table.category),
}));

// ============================================
// API KEYS (For integrations)
// ============================================

export const apiKeys = sqliteTable('api_keys', {
  id: text('id').primaryKey(), // UUID
  userId: text('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),

  name: text('name').notNull(),
  keyHash: text('key_hash').notNull(), // SHA-256 hash of the API key
  keyPrefix: text('key_prefix').notNull(), // First 8 chars for identification

  // Permissions
  permissions: text('permissions', { mode: 'json' }).$type<string[]>(),

  // Rate limiting
  rateLimit: integer('rate_limit').default(100), // requests per minute

  lastUsedAt: integer('last_used_at', { mode: 'timestamp' }),
  expiresAt: integer('expires_at', { mode: 'timestamp' }),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  userIdIdx: index('api_keys_user_id_idx').on(table.userId),
  keyHashIdx: uniqueIndex('api_keys_key_hash_idx').on(table.keyHash),
}));

// ============================================
// SESSIONS
// ============================================

export const sessions = sqliteTable('sessions', {
  id: text('id').primaryKey(), // Session token
  userId: text('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),

  ipAddress: text('ip_address'),
  userAgent: text('user_agent'),

  expiresAt: integer('expires_at', { mode: 'timestamp' }).notNull(),
  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  userIdIdx: index('sessions_user_id_idx').on(table.userId),
  expiresAtIdx: index('sessions_expires_at_idx').on(table.expiresAt),
}));

// ============================================
// WEBHOOKS (User-configured webhooks)
// ============================================

export const webhooks = sqliteTable('webhooks', {
  id: text('id').primaryKey(), // UUID
  userId: text('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),

  url: text('url').notNull(),
  secret: text('secret').notNull(), // For HMAC signature

  // Events to subscribe to
  events: text('events', { mode: 'json' }).$type<string[]>(),

  isActive: integer('is_active', { mode: 'boolean' }).default(true),

  // Stats
  successCount: integer('success_count').default(0),
  failureCount: integer('failure_count').default(0),
  lastTriggeredAt: integer('last_triggered_at', { mode: 'timestamp' }),
  lastFailureAt: integer('last_failure_at', { mode: 'timestamp' }),
  lastFailureReason: text('last_failure_reason'),

  createdAt: integer('created_at', { mode: 'timestamp' })
    .default(sql`(unixepoch())`)
    .notNull(),
}, (table) => ({
  userIdIdx: index('webhooks_user_id_idx').on(table.userId),
}));

// ============================================
// TYPE EXPORTS
// ============================================

export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;

export type Document = typeof documents.$inferSelect;
export type NewDocument = typeof documents.$inferInsert;

export type DocumentField = typeof documentFields.$inferSelect;
export type NewDocumentField = typeof documentFields.$inferInsert;

export type Recipient = typeof recipients.$inferSelect;
export type NewRecipient = typeof recipients.$inferInsert;

export type AuditLog = typeof auditLogs.$inferSelect;
export type NewAuditLog = typeof auditLogs.$inferInsert;

export type Template = typeof templates.$inferSelect;
export type NewTemplate = typeof templates.$inferInsert;

export type ApiKey = typeof apiKeys.$inferSelect;
export type NewApiKey = typeof apiKeys.$inferInsert;

export type Session = typeof sessions.$inferSelect;
export type NewSession = typeof sessions.$inferInsert;

export type Webhook = typeof webhooks.$inferSelect;
export type NewWebhook = typeof webhooks.$inferInsert;
```

#### `src/lib/server/db/index.ts`

```typescript
import { drizzle } from 'drizzle-orm/libsql';
import { createClient } from '@libsql/client/web';
import * as schema from './schema';

// For Cloudflare Workers, use @libsql/client/web
const client = createClient({
  url: process.env.TURSO_CONNECTION_URL!,
  authToken: process.env.TURSO_AUTH_TOKEN!,
});

export const db = drizzle(client, { schema });

// Re-export schema for convenience
export * from './schema';
```

---

## 4. Cloudflare Workers Structure

### 4.1 SvelteKit API Routes (Primary Backend)

With `adapter-cloudflare`, your SvelteKit app IS the Cloudflare Worker. All API endpoints in `src/routes/api/` run on the edge.

#### Rate Limiting with Cloudflare

`src/lib/server/utils/rate-limit.ts`

```typescript
import { error } from '@sveltejs/kit';

interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
}

const rateLimitStore = new Map<string, { count: number; resetAt: number }>();

export function rateLimit(
  identifier: string,
  config: RateLimitConfig = { windowMs: 60000, maxRequests: 60 }
): void {
  const now = Date.now();
  const key = identifier;

  const existing = rateLimitStore.get(key);

  if (!existing || now > existing.resetAt) {
    rateLimitStore.set(key, { count: 1, resetAt: now + config.windowMs });
    return;
  }

  if (existing.count >= config.maxRequests) {
    throw error(429, 'Too many requests. Please try again later.');
  }

  existing.count++;
}

// For production, use Cloudflare KV or Durable Objects
export async function rateLimitWithKV(
  kv: KVNamespace,
  identifier: string,
  config: RateLimitConfig = { windowMs: 60000, maxRequests: 60 }
): Promise<void> {
  const key = `ratelimit:${identifier}`;
  const now = Date.now();

  const stored = await kv.get(key, 'json') as { count: number; resetAt: number } | null;

  if (!stored || now > stored.resetAt) {
    await kv.put(key, JSON.stringify({ count: 1, resetAt: now + config.windowMs }), {
      expirationTtl: Math.ceil(config.windowMs / 1000),
    });
    return;
  }

  if (stored.count >= config.maxRequests) {
    throw error(429, 'Too many requests. Please try again later.');
  }

  await kv.put(key, JSON.stringify({ ...stored, count: stored.count + 1 }), {
    expirationTtl: Math.ceil((stored.resetAt - now) / 1000),
  });
}
```

### 4.2 Key API Endpoints

#### `src/routes/api/upload/presigned/+server.ts`

```typescript
import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { nanoid } from 'nanoid';
import {
  R2_ACCOUNT_ID,
  R2_ACCESS_KEY_ID,
  R2_SECRET_ACCESS_KEY,
  R2_BUCKET_NAME
} from '$env/static/private';

const s3Client = new S3Client({
  region: 'auto',
  endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: R2_ACCESS_KEY_ID,
    secretAccessKey: R2_SECRET_ACCESS_KEY,
  },
});

export const POST: RequestHandler = async ({ locals, request }) => {
  // Ensure user is authenticated
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  const { fileName, contentType, fileSize } = await request.json();

  // Validate
  if (contentType !== 'application/pdf') {
    throw error(400, 'Only PDF files are allowed');
  }

  if (fileSize > 50 * 1024 * 1024) { // 50MB limit
    throw error(400, 'File size exceeds 50MB limit');
  }

  // Generate unique key
  const key = `uploads/${locals.user.id}/${nanoid()}.pdf`;

  // Create presigned URL
  const command = new PutObjectCommand({
    Bucket: R2_BUCKET_NAME,
    Key: key,
    ContentType: contentType,
    ContentLength: fileSize,
  });

  const presignedUrl = await getSignedUrl(s3Client, command, {
    expiresIn: 300, // 5 minutes
  });

  return json({
    presignedUrl,
    key,
    expiresIn: 300,
  });
};
```

#### `src/routes/api/documents/+server.ts`

```typescript
import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db, documents, documentFields, recipients, auditLogs } from '$lib/server/db';
import { eq, desc, and } from 'drizzle-orm';
import { nanoid } from 'nanoid';
import { createAuditLog } from '$lib/server/utils/audit';

// GET - List user's documents
export const GET: RequestHandler = async ({ locals, url }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  const status = url.searchParams.get('status');
  const limit = parseInt(url.searchParams.get('limit') || '20');
  const offset = parseInt(url.searchParams.get('offset') || '0');

  const conditions = [eq(documents.userId, locals.user.id)];

  if (status) {
    conditions.push(eq(documents.status, status as any));
  }

  const docs = await db.query.documents.findMany({
    where: and(...conditions),
    orderBy: [desc(documents.createdAt)],
    limit,
    offset,
    with: {
      recipients: true,
    },
  });

  return json({ documents: docs });
};

// POST - Create new document
export const POST: RequestHandler = async ({ locals, request }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  const body = await request.json();
  const {
    title,
    description,
    storageType,
    storageId,
    originalFileName,
    fileSize,
    pageCount,
    isTemplate,
  } = body;

  const docId = nanoid();

  const [doc] = await db.insert(documents).values({
    id: docId,
    userId: locals.user.id,
    title,
    description,
    storageType,
    storageId,
    originalFileName,
    fileSize,
    pageCount,
    isTemplate: isTemplate || false,
    status: 'draft',
  }).returning();

  // Create audit log
  await createAuditLog(db, {
    documentId: docId,
    userId: locals.user.id,
    action: 'document_created',
    ipAddress: request.headers.get('cf-connecting-ip') || undefined,
    userAgent: request.headers.get('user-agent') || undefined,
  });

  return json({ document: doc }, { status: 201 });
};
```

#### `src/routes/api/documents/[id]/sign/+server.ts`

```typescript
import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db, documents, documentFields, recipients, auditLogs } from '$lib/server/db';
import { eq, and } from 'drizzle-orm';
import { createAuditLog } from '$lib/server/utils/audit';
import { sendSignatureCompleteEmail } from '$lib/server/services/resend';

// POST - Submit signature for a field
export const POST: RequestHandler = async ({ params, request, locals }) => {
  const { id: documentId } = params;
  const { recipientToken, fieldId, signatureData } = await request.json();

  // Validate recipient token
  const recipient = await db.query.recipients.findFirst({
    where: and(
      eq(recipients.documentId, documentId),
      eq(recipients.accessToken, recipientToken),
    ),
    with: {
      document: true,
    },
  });

  if (!recipient) {
    throw error(404, 'Invalid signing link');
  }

  if (recipient.tokenExpiresAt && new Date(recipient.tokenExpiresAt * 1000) < new Date()) {
    throw error(410, 'Signing link has expired');
  }

  if (recipient.status === 'signed') {
    throw error(400, 'You have already signed this document');
  }

  // Update the field with signature
  await db.update(documentFields)
    .set({
      value: signatureData, // Base64 signature image
      filledAt: new Date(),
      filledByIp: request.headers.get('cf-connecting-ip'),
    })
    .where(
      and(
        eq(documentFields.id, fieldId),
        eq(documentFields.recipientId, recipient.id),
      )
    );

  // Check if all fields for this recipient are filled
  const remainingFields = await db.query.documentFields.findMany({
    where: and(
      eq(documentFields.recipientId, recipient.id),
      eq(documentFields.value, null),
    ),
  });

  if (remainingFields.length === 0) {
    // Mark recipient as signed
    await db.update(recipients)
      .set({
        status: 'signed',
        signedAt: new Date(),
        signingIp: request.headers.get('cf-connecting-ip'),
        userAgent: request.headers.get('user-agent'),
      })
      .where(eq(recipients.id, recipient.id));

    // Create audit log
    await createAuditLog(db, {
      documentId,
      recipientId: recipient.id,
      action: 'document_signed',
      ipAddress: request.headers.get('cf-connecting-ip') || undefined,
      userAgent: request.headers.get('user-agent') || undefined,
      metadata: { email: recipient.email },
    });

    // Check if all recipients have signed
    const pendingRecipients = await db.query.recipients.findMany({
      where: and(
        eq(recipients.documentId, documentId),
        eq(recipients.status, 'pending'),
      ),
    });

    if (pendingRecipients.length === 0) {
      // Document complete - update status
      await db.update(documents)
        .set({
          status: 'completed',
          signedAt: new Date(),
        })
        .where(eq(documents.id, documentId));

      // Create completion audit log
      await createAuditLog(db, {
        documentId,
        action: 'document_completed',
      });

      // Send completion emails
      await sendSignatureCompleteEmail(recipient.document);
    }
  }

  return json({
    success: true,
    remainingFields: remainingFields.length,
  });
};
```

---

## 5. Critical Configuration Files

### 5.1 `wrangler.toml`

```toml
name = "signsimple"
compatibility_date = "2025-01-01"
compatibility_flags = ["nodejs_compat"]

# The SvelteKit adapter handles this
main = ".svelte-kit/cloudflare/_worker.js"

[assets]
binding = "ASSETS"
directory = ".svelte-kit/cloudflare"

# Environment variables (secrets set via `wrangler secret put`)
[vars]
PUBLIC_GOOGLE_API_KEY = ""
PUBLIC_GOOGLE_CLIENT_ID = ""
PUBLIC_STRIPE_PUBLISHABLE_KEY = ""
PUBLIC_APP_URL = "https://signsimple.io"

# R2 Bucket binding
[[r2_buckets]]
binding = "R2_BUCKET"
bucket_name = "signsimple-documents"
preview_bucket_name = "signsimple-documents-preview"

# KV Namespace for rate limiting and caching
[[kv_namespaces]]
binding = "KV"
id = "your-kv-namespace-id"
preview_id = "your-kv-preview-namespace-id"

# Durable Objects (optional, for real-time collaboration)
# [[durable_objects.bindings]]
# name = "DOCUMENT_SESSION"
# class_name = "DocumentSession"

# Development settings
[dev]
port = 8787
local_protocol = "http"

# Production environment
[env.production]
vars = { PUBLIC_APP_URL = "https://signsimple.io" }

[[env.production.r2_buckets]]
binding = "R2_BUCKET"
bucket_name = "signsimple-documents-prod"

# Secrets to set (DO NOT put actual values here):
# wrangler secret put TURSO_CONNECTION_URL
# wrangler secret put TURSO_AUTH_TOKEN
# wrangler secret put GOOGLE_CLIENT_SECRET
# wrangler secret put STRIPE_SECRET_KEY
# wrangler secret put STRIPE_WEBHOOK_SECRET
# wrangler secret put RESEND_API_KEY
# wrangler secret put R2_ACCESS_KEY_ID
# wrangler secret put R2_SECRET_ACCESS_KEY
# wrangler secret put SESSION_SECRET
```

### 5.2 `drizzle.config.ts`

```typescript
import { defineConfig } from 'drizzle-kit';
import * as dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

export default defineConfig({
  schema: './src/lib/server/db/schema.ts',
  out: './drizzle/migrations',
  dialect: 'turso',
  dbCredentials: {
    url: process.env.TURSO_CONNECTION_URL!,
    authToken: process.env.TURSO_AUTH_TOKEN!,
  },
  verbose: true,
  strict: true,
});
```

### 5.3 `svelte.config.js`

```javascript
import adapter from '@sveltejs/adapter-cloudflare';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),

  kit: {
    adapter: adapter({
      // Wrangler configuration path (optional, uses wrangler.toml by default)
      config: 'wrangler.toml',

      // Platform proxy for local development
      platformProxy: {
        configPath: 'wrangler.toml',
        environment: undefined,
        persist: '.wrangler/state',
      },

      // Routes configuration
      routes: {
        include: ['/*'],
        exclude: ['<all>'],
      },
    }),

    alias: {
      $components: 'src/lib/components',
      $stores: 'src/lib/stores',
      $utils: 'src/lib/utils',
      $types: 'src/lib/types',
    },

    // CSP headers (adjust as needed)
    csp: {
      mode: 'auto',
      directives: {
        'script-src': ['self', 'https://apis.google.com', 'https://accounts.google.com'],
        'frame-src': ['self', 'https://docs.google.com', 'https://drive.google.com'],
        'connect-src': ['self', 'https://*.googleapis.com', 'https://*.google.com'],
      },
    },
  },
};

export default config;
```

### 5.4 `vite.config.ts`

```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],

  optimizeDeps: {
    exclude: ['@libsql/client'],
  },

  build: {
    target: 'esnext',
    // Increase chunk size warning limit for PDF libraries
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          'pdf-lib': ['pdf-lib'],
          'pdfjs': ['pdfjs-dist'],
        },
      },
    },
  },

  // For local development with Cloudflare bindings
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV),
  },
});
```

### 5.5 `tsconfig.json`

```json
{
  "extends": "./.svelte-kit/tsconfig.json",
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "sourceMap": true,
    "strict": true,
    "moduleResolution": "bundler",
    "target": "ESNext",
    "module": "ESNext",
    "types": ["@cloudflare/workers-types"]
  }
}
```

### 5.6 `src/app.d.ts`

```typescript
/// <reference types="@sveltejs/adapter-cloudflare" />
/// <reference types="@cloudflare/workers-types" />

import type { User, Session } from '$lib/server/db/schema';

declare global {
  namespace App {
    interface Error {
      message: string;
      code?: string;
    }

    interface Locals {
      user: User | null;
      session: Session | null;
    }

    interface PageData {
      user: User | null;
    }

    interface Platform {
      env: {
        R2_BUCKET: R2Bucket;
        KV: KVNamespace;
        TURSO_CONNECTION_URL: string;
        TURSO_AUTH_TOKEN: string;
        GOOGLE_CLIENT_SECRET: string;
        STRIPE_SECRET_KEY: string;
        STRIPE_WEBHOOK_SECRET: string;
        RESEND_API_KEY: string;
        SESSION_SECRET: string;
      };
      context: ExecutionContext;
      caches: CacheStorage & { default: Cache };
    }
  }
}

export {};
```

### 5.7 `.env.example`

```bash
# ============================================
# Turso Database
# ============================================
TURSO_CONNECTION_URL=libsql://your-database.turso.io
TURSO_AUTH_TOKEN=your-auth-token

# ============================================
# Google OAuth & Picker
# ============================================
PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
PUBLIC_GOOGLE_API_KEY=your-api-key

# ============================================
# Cloudflare R2
# ============================================
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=signsimple-documents

# ============================================
# Stripe
# ============================================
PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# ============================================
# Resend Email
# ============================================
RESEND_API_KEY=re_xxx

# ============================================
# App Configuration
# ============================================
PUBLIC_APP_URL=http://localhost:5173
SESSION_SECRET=generate-a-secure-random-string-here
```

---

## 6. Package.json Dependencies

```json
{
  "name": "signsimple",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "wrangler pages dev .svelte-kit/cloudflare",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    "check:watch": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --watch",
    "lint": "eslint .",
    "format": "prettier --write .",
    "test": "vitest",
    "test:unit": "vitest run",
    "test:e2e": "playwright test",
    "db:generate": "drizzle-kit generate",
    "db:migrate": "drizzle-kit migrate",
    "db:push": "drizzle-kit push",
    "db:studio": "drizzle-kit studio",
    "deploy": "npm run build && wrangler pages deploy .svelte-kit/cloudflare",
    "deploy:prod": "npm run build && wrangler pages deploy .svelte-kit/cloudflare --env production"
  },
  "dependencies": {
    "@aws-sdk/client-s3": "^3.705.0",
    "@aws-sdk/s3-request-presigner": "^3.705.0",
    "@libsql/client": "^0.14.0",
    "drizzle-orm": "^0.38.3",
    "nanoid": "^5.0.9",
    "pdf-lib": "^1.17.1",
    "pdfjs-dist": "^4.9.155",
    "resend": "^4.0.1",
    "stripe": "^17.4.0"
  },
  "devDependencies": {
    "@cloudflare/workers-types": "^4.20241230.0",
    "@playwright/test": "^1.49.1",
    "@sveltejs/adapter-cloudflare": "^4.8.0",
    "@sveltejs/kit": "^2.15.1",
    "@sveltejs/vite-plugin-svelte": "^4.0.4",
    "@types/node": "^22.10.5",
    "autoprefixer": "^10.4.20",
    "drizzle-kit": "^0.30.1",
    "eslint": "^9.17.0",
    "eslint-plugin-svelte": "^2.46.1",
    "postcss": "^8.4.49",
    "prettier": "^3.4.2",
    "prettier-plugin-svelte": "^3.3.2",
    "svelte": "^5.16.2",
    "svelte-check": "^4.1.4",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.2",
    "vite": "^6.0.7",
    "vitest": "^2.1.8",
    "wrangler": "^3.99.0"
  },
  "engines": {
    "node": ">=20"
  }
}
```

---

## 7. Deployment Pipeline

### 7.1 Initial Setup

```bash
# 1. Install dependencies
npm install

# 2. Create Turso database
turso db create signsimple
turso db show signsimple --url  # Get the URL
turso db tokens create signsimple  # Get auth token

# 3. Create Cloudflare R2 bucket
wrangler r2 bucket create signsimple-documents

# 4. Create KV namespace
wrangler kv:namespace create "KV"
wrangler kv:namespace create "KV" --preview

# 5. Set up secrets
wrangler secret put TURSO_CONNECTION_URL
wrangler secret put TURSO_AUTH_TOKEN
wrangler secret put GOOGLE_CLIENT_SECRET
wrangler secret put STRIPE_SECRET_KEY
wrangler secret put STRIPE_WEBHOOK_SECRET
wrangler secret put RESEND_API_KEY
wrangler secret put SESSION_SECRET

# 6. Run database migrations
npm run db:generate
npm run db:migrate

# 7. Deploy
npm run deploy
```

### 7.2 CI/CD with GitHub Actions

`.github/workflows/deploy.yml`

```yaml
name: Deploy to Cloudflare

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run type check
        run: npm run check

      - name: Run linter
        run: npm run lint

      - name: Run tests
        run: npm run test:unit

  deploy-preview:
    needs: test
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
        env:
          PUBLIC_GOOGLE_CLIENT_ID: ${{ secrets.PUBLIC_GOOGLE_CLIENT_ID }}
          PUBLIC_GOOGLE_API_KEY: ${{ secrets.PUBLIC_GOOGLE_API_KEY }}
          PUBLIC_STRIPE_PUBLISHABLE_KEY: ${{ secrets.PUBLIC_STRIPE_PUBLISHABLE_KEY }}
          PUBLIC_APP_URL: ${{ secrets.PUBLIC_APP_URL }}

      - name: Deploy to Cloudflare Pages (Preview)
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy .svelte-kit/cloudflare --project-name=signsimple

  deploy-production:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
        env:
          PUBLIC_GOOGLE_CLIENT_ID: ${{ secrets.PUBLIC_GOOGLE_CLIENT_ID }}
          PUBLIC_GOOGLE_API_KEY: ${{ secrets.PUBLIC_GOOGLE_API_KEY }}
          PUBLIC_STRIPE_PUBLISHABLE_KEY: ${{ secrets.PUBLIC_STRIPE_PUBLISHABLE_KEY }}
          PUBLIC_APP_URL: https://signsimple.io

      - name: Deploy to Cloudflare Pages (Production)
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy .svelte-kit/cloudflare --project-name=signsimple --branch=main

  migrate-database:
    needs: deploy-production
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run migrations
        run: npm run db:migrate
        env:
          TURSO_CONNECTION_URL: ${{ secrets.TURSO_CONNECTION_URL }}
          TURSO_AUTH_TOKEN: ${{ secrets.TURSO_AUTH_TOKEN }}
```

### 7.3 GitHub Secrets Required

```
CLOUDFLARE_API_TOKEN        # Cloudflare API token with Pages edit permission
CLOUDFLARE_ACCOUNT_ID       # Your Cloudflare account ID
TURSO_CONNECTION_URL        # Turso database URL
TURSO_AUTH_TOKEN           # Turso auth token
PUBLIC_GOOGLE_CLIENT_ID    # Google OAuth client ID
PUBLIC_GOOGLE_API_KEY      # Google API key for Picker
PUBLIC_STRIPE_PUBLISHABLE_KEY  # Stripe publishable key
PUBLIC_APP_URL             # App URL (https://signsimple.io)
```

---

## 8. Architecture Decisions & Rationale

### Why Google Picker + drive.file Scope?

1. **No CASA Audit Required**: The `drive.file` scope is classified as "non-sensitive" by Google
2. **Instant Verification**: No 4-8 week security review process
3. **User Control**: Users explicitly select which files the app can access
4. **Cost Savings**: CASA Tier 2 audits cost $15,000-$75,000

### Why Turso over Cloudflare D1?

1. **Global Replication**: Turso replicates to edge locations automatically
2. **Better SDK**: drizzle-orm works seamlessly with libSQL
3. **Larger Limits**: D1 has 10GB max, Turso scales higher
4. **Standalone Service**: Not locked into Cloudflare ecosystem

### Why pdf-lib + PDF.js?

1. **pdf-lib**: Modification/creation (adding signatures, text)
2. **PDF.js**: Rendering for display (canvas-based, accurate)
3. **Client-Side**: No server processing needed for basic operations
4. **No Dependencies**: Both work in pure JavaScript

### Why R2 for Temporary Storage?

1. **Zero Egress Fees**: Download signed PDFs free
2. **S3 Compatible**: Easy migration if needed
3. **Cloudflare Integration**: Native bindings in Workers
4. **Auto-Delete**: Lifecycle rules for temp files

---

## Sources

- [Google Picker API Overview](https://developers.google.com/workspace/drive/picker/guides/overview)
- [Google Picker API Code Sample](https://developers.google.com/workspace/drive/picker/guides/sample)
- [Google Drive API Scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
- [SvelteKit Cloudflare Adapter](https://svelte.dev/docs/kit/adapter-cloudflare)
- [Cloudflare Pages SvelteKit Guide](https://developers.cloudflare.com/pages/framework-guides/deploy-a-svelte-kit-site/)
- [Drizzle ORM with Turso](https://orm.drizzle.team/docs/tutorials/drizzle-with-turso)
- [Turso + Drizzle Documentation](https://docs.turso.tech/sdk/ts/orm/drizzle)
- [Cloudflare Workers + Turso Integration](https://developers.cloudflare.com/workers/tutorials/connect-to-turso-using-workers/)
- [pdf-lib Documentation](https://pdf-lib.js.org/)
- [Cloudflare R2 Presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/)
- [SvelteKit R2 Upload Tutorial](https://www.okupter.com/blog/upload-files-cloudflare-r2-in-sveltekit)
