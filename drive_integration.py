"""
Google Drive Integration — MCP Feature.

Permite que o agente busque documentos de seguro diretamente
do Google Drive, em vez de depender de upload manual.

No mundo real: clientes de insurance salvam docs num Drive compartilhado.
O agente monitora a pasta e processa novos documentos automaticamente.

SETUP:
1. Habilite a Google Drive API no GCP Console
2. Crie uma Service Account e baixe o JSON de credenciais
3. Compartilhe a pasta do Drive com o email da Service Account
4. Adicione no .env:
   GOOGLE_DRIVE_FOLDER_ID=seu-folder-id
   GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
"""

import os
import json
import tempfile
from langchain_core.tools import tool


@tool
def fetch_document_from_drive(file_name: str) -> str:
    """
    Busca um documento PDF do Google Drive pelo nome.
    Baixa o arquivo para um diretório temporário e retorna o caminho local.

    Use esta tool quando o usuário mencionar um documento que está no Google Drive,
    ou quando precisar buscar o documento mais recente de uma pasta monitorada.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        import io

        # Autentica com Service Account
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )

        service = build("drive", "v3", credentials=credentials)

        # Busca o arquivo pelo nome na pasta configurada
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        query = f"name contains '{file_name}' and mimeType='application/pdf'"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        results = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=1,
        ).execute()

        files = results.get("files", [])

        if not files:
            return json.dumps({"error": f"No PDF found matching '{file_name}' in Drive"})

        file = files[0]
        file_id = file["id"]

        # Baixa o arquivo pra um temp file
        request = service.files().get_media(fileId=file_id)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)

        downloader = MediaIoBaseDownload(io.BytesIO(), request)
        with open(tmp.name, "wb") as f:
            request = service.files().get_media(fileId=file_id)
            content = request.execute()
            f.write(content)

        return json.dumps({
            "local_path": tmp.name,
            "drive_file_name": file["name"],
            "drive_file_id": file_id,
            "modified": file.get("modifiedTime"),
        })

    except ImportError:
        return json.dumps({
            "error": "Google Drive dependencies not installed. Run: pip install google-auth google-api-python-client"
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch from Drive: {str(e)}"})


@tool
def list_pending_documents() -> str:
    """
    Lista documentos PDF pendentes de análise na pasta do Google Drive.
    Retorna os nomes e datas dos documentos encontrados.

    Use esta tool quando o usuário quiser ver quais documentos estão
    aguardando análise, ou quando precisar processar um batch.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )

        service = build("drive", "v3", credentials=credentials)

        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        query = "mimeType='application/pdf'"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        results = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, modifiedTime, size)",
            orderBy="modifiedTime desc",
            pageSize=20,
        ).execute()

        files = results.get("files", [])

        if not files:
            return json.dumps({"message": "No PDF documents found in the monitored folder"})

        documents = [
            {
                "name": f["name"],
                "id": f["id"],
                "modified": f.get("modifiedTime"),
                "size_bytes": f.get("size"),
            }
            for f in files
        ]

        return json.dumps({"documents": documents, "count": len(documents)})

    except ImportError:
        return json.dumps({
            "error": "Google Drive dependencies not installed. Run: pip install google-auth google-api-python-client"
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to list Drive documents: {str(e)}"})
