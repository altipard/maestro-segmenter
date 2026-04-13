# Maestro Segmenter

gRPC service for text segmentation. Splits text into chunks using semantic boundaries with Markdown awareness — optimized for RAG pipelines.

## Why gRPC?

Text segmentation is a tight inner-loop operation in RAG pipelines — called repeatedly with varying payload sizes. gRPC is a natural fit:

- **Binary-native** — Protobuf encodes text and parameters without JSON serialization overhead. No escaping, no string quoting, no Base64 for binary content.
- **Strongly typed contracts** — The `.proto` file defines the exact request/response shape. Segment length, overlap, and file content are typed fields — not string-encoded JSON that needs runtime parsing.
- **Connection multiplexing** — HTTP/2 lets Maestro send many segmentation requests over a single connection. Useful when processing a batch of documents in parallel.
- **Language-agnostic** — The same `.proto` contract generates clients for Python, Go, TypeScript, Rust. You can call this service from anything, or rewrite the service in another language without changing clients.
- **Low-latency** — Binary framing and header compression keep per-request overhead minimal. For a service that may be called hundreds of times during a single document ingestion pipeline, this adds up.

For Maestro, gRPC provides the same interface pattern across both the Extractor and Segmenter services — one protocol, one contract style, consistent tooling.

## Architecture

```
┌──────────────┐  gRPC :50051  ┌───────────────────┐
│   Maestro    │──────────────▶│    Segmenter      │
│  (Platform)  │               │                   │
└──────────────┘               │  semantic-text-   │
                               │  splitter (Rust)  │
                               └───────────────────┘
```

Maestro Platform calls the Segmenter over gRPC when text needs to be chunked for embedding and retrieval.

## How It Works

The segmenter uses [semantic-text-splitter](https://github.com/benbrandt/text-splitter), a Rust-backed library, for high-quality text chunking:

- **Markdown detection** — Automatically detects Markdown content and uses `MarkdownSplitter` which respects heading hierarchy, code blocks, and list structure.
- **Plain text fallback** — Non-Markdown content uses `TextSplitter` which splits at semantic boundaries (paragraphs, sentences, words).
- **Configurable** — Segment length and overlap are configurable per request.

## Quick Start

### Docker (recommended)

```bash
docker run -p 50051:50051 ghcr.io/altipard/maestro-segmenter
```

### Docker Compose (with Maestro)

```yaml
segmenter:
  image: ghcr.io/altipard/maestro-segmenter
```

Configure Maestro to use it:

```yaml
segmenters:
  default:
    type: grpc
    url: grpc://segmenter:50051
    segment_length: 1000
    segment_overlap: 100
```

### Local

```bash
pip install -r requirements.txt
python main.py
```

## gRPC API

Defined in `segmenter.proto`:

```protobuf
service Segmenter {
  rpc Segment (SegmentRequest) returns (SegmentResponse);
}

message SegmentRequest {
  File file = 1;
  optional int32 segment_length = 2;
  optional int32 segment_overlap = 3;
}

message SegmentResponse {
  repeated Segment segments = 1;
}

message File {
  string name = 1;
  bytes content = 2;
  string content_type = 3;
}

message Segment {
  string text = 1;
}
```

### Request Parameters

| Field | Default | Description |
|-------|---------|-------------|
| `file.content` | required | Text content as bytes (UTF-8) |
| `segment_length` | 1000 | Maximum characters per chunk |
| `segment_overlap` | 0 | Character overlap between chunks |

### Regenerate Proto Files

```bash
task generate
```

## Available Task Commands

| Command | Description |
|---------|-------------|
| `task run` | Run via Docker |
| `task generate` | Regenerate protobuf Python files |
| `task publish` | Build and push multi-arch Docker image |

## Port

| Service | Port | Protocol |
|---------|------|----------|
| Segmenter | 50051 | gRPC |

## Note on Maestro's Built-in Segmenter

Maestro Platform includes a built-in `type: text` segmenter that uses the same `semantic-text-splitter` library. This gRPC service is only needed if you want to run segmentation in a separate process for scaling or isolation. For most setups, `type: text` in the Maestro config is sufficient.
