# dependency-map/n-src-main-py-d1a726

[解析トップへ戻る](../../README.md)

確認済みファイル: `src/main.py`

解析: Python AST。静的なimport／export参照です。関数の実行順序やHTTP通信は表していません。

宣言: `main`

- `sys` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `os` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `argparse` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `importlib` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `logging` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `dotenv` → 外部・標準ライブラリ・別名など。ローカル対応先は未確定
- `mcp_server` → `src/mcp_server.py`（内容確認済み）
- `rag_tools` → `src/rag_tools.py`（内容確認済み）


```mermaid
graph TD
    source["ソース\nsrc/main.py"]
    n-sys-b4c56e["sys\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-sys-b4c56e
    n-os-999a34["os\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-os-999a34
    n-argparse-e750ee["argparse\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-argparse-e750ee
    n-importlib-a5e0f9["importlib\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-importlib-a5e0f9
    n-logging-42f7b0["logging\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-logging-42f7b0
    n-dotenv-4de95c["dotenv\n外部・別名・未解決"]
    source -->|"Python AST: import／export"| n-dotenv-4de95c
    n-mcp-server-affc9b["mcp_server\nsrc/mcp_server.py"]
    source -->|"Python AST: import／export"| n-mcp-server-affc9b
    n-rag-tools-48aafe["rag_tools\nsrc/rag_tools.py"]
    source -->|"Python AST: import／export"| n-rag-tools-48aafe
```

## 要素の説明

### n-argparse-e750ee

参照名: `argparse`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-dotenv-4de95c

参照名: `dotenv`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-importlib-a5e0f9

参照名: `importlib`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-logging-42f7b0

参照名: `logging`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-mcp-server-affc9b

参照名: `mcp_server`

対応する実在ソース: `src/mcp_server.py`。内容確認済み。

### n-os-999a34

参照名: `os`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### n-rag-tools-48aafe

参照名: `rag_tools`

対応する実在ソース: `src/rag_tools.py`。内容確認済み。

### n-sys-b4c56e

参照名: `sys`

ローカルのソース対応先を確定できませんでした。外部ライブラリ、標準ライブラリ、型別名などを区別する追加確認が必要です。

### source

`src/main.py` の内容を確認しました。

