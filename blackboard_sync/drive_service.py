import logging
from pathlib import Path

_GOOGLE_IMPORT_ERROR = None

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    _GOOGLE_DRIVE_AVAILABLE = True
except ModuleNotFoundError as import_error:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    MediaFileUpload = None
    _GOOGLE_DRIVE_AVAILABLE = False
    _GOOGLE_IMPORT_ERROR = import_error

logger = logging.getLogger(__name__)


class DriveService:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    AVAILABLE = _GOOGLE_DRIVE_AVAILABLE

    def __init__(self, credentials_path: Path, token_path: Path):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.creds = None

    @staticmethod
    def _query_literal(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    def authenticates(self) -> bool:
        """Authenticate with Google Drive API."""
        if not self.AVAILABLE:
            logger.warning(
                "Google Drive dependencies are not installed; skipping Drive integration (%s)",
                _GOOGLE_IMPORT_ERROR
            )
            return False

        self.creds = None
        
        if self.token_path.exists():
            try:
                self.creds = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)
            except Exception:
                logger.warning("Token file seems invalid, regenerating...")

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    self.creds = None
            
            if not self.creds:
                if not self.credentials_path.exists():
                    logger.error(f"Credentials file not found at {self.credentials_path}")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.exception(f"Authentication flow failed: {e}")
                    return False

            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())

        try:
            self.service = build('drive', 'v3', credentials=self.creds)
            return True
        except Exception:
            logger.exception("Failed to build Drive service")
            return False

    def get_user_email(self) -> str | None:
        """Get the email of the authenticated user."""
        if not self.service:
            return None
        try:
            about = self.service.about().get(fields="user").execute()
            return about['user']['emailAddress']
        except Exception:
            return None

    def find_folder(self, name: str, parent_id: str | None = None) -> str | None:
        """Find a folder by name inside a parent folder."""
        if not self.service:
            return None

        query = (
            "mimeType='application/vnd.google-apps.folder' and "
            f"name={self._query_literal(name)} and trashed=false"
        )
        if parent_id:
            query += f" and {self._query_literal(parent_id)} in parents"
        
        try:
            results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = results.get('files', [])
            if files:
                return files[0]['id']
        except Exception:
            logger.exception(f"Error finding folder {name}")
        return None

    def create_folder(self, name: str, parent_id: str | None = None) -> str | None:
        """Create a folder."""
        if not self.service:
            return None

        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        try:
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            return file.get('id')
        except Exception:
            logger.exception(f"Error creating folder {name}")
            return None

    def ensure_folder(self, name: str, parent_id: str | None = None) -> str | None:
        """Find or create a folder."""
        folder_id = self.find_folder(name, parent_id)
        if folder_id:
            return folder_id
        return self.create_folder(name, parent_id)

    def folder_exists(self, folder_id: str) -> bool:
        """Check whether a folder id is still accessible and points to a folder."""
        if not self.service:
            return False

        try:
            file = self.service.files().get(
                fileId=folder_id,
                fields='id, mimeType, trashed'
            ).execute()
        except Exception:
            logger.exception("Error validating folder %s", folder_id)
            return False

        return (
            not file.get('trashed', False)
            and file.get('mimeType') == 'application/vnd.google-apps.folder'
        )

    def upload_file(self, local_path: Path, parent_id: str) -> bool:
        """Upload or update a file."""
        if not self.service:
            return False

        name = local_path.name
        
        # Check if file exists to update or create
        existing_id = None
        try:
            query = (
                f"name={self._query_literal(name)} and "
                f"{self._query_literal(parent_id)} in parents and trashed=false"
            )
            results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
            files = results.get('files', [])
            if files:
                existing_id = files[0]['id']
        except Exception:
            logger.exception("Error querying existing file %s", name)

        file_metadata = {'name': name}
        media = MediaFileUpload(str(local_path), resumable=True)

        try:
            if existing_id:
                self.service.files().update(
                    fileId=existing_id,
                    media_body=media
                ).execute()
                logger.debug(f"Updated file {name}")
            else:
                file_metadata['parents'] = [parent_id]
                self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logger.debug(f"Uploaded file {name}")
            return True
        except Exception:
            logger.exception(f"Error uploading file {name}")
            return False

    def mirror_tree(self, local_root: Path, drive_root_id: str) -> None:
        """Recursively mirror local directory structure to Drive."""
        if not self.service:
            return

        for item in local_root.iterdir():
            if item.is_dir():
                # Ignore hidden folders
                if item.name.startswith('.'):
                    continue
                    
                folder_id = self.ensure_folder(item.name, drive_root_id)
                if folder_id:
                    self.mirror_tree(item, folder_id)
            elif item.is_file():
                self.upload_file(item, drive_root_id)
