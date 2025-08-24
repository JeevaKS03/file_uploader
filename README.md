# File Manager Web Application

A modern, responsive web application for file handling with upload, download, and delete functionality.

## Features

- **Cloud Storage**: All files stored securely in Cloudinary cloud
- **File Upload**: Drag and drop or click to upload files
- **File Display**: View all uploaded files with file information (name, size, modification date)
- **File Download**: Download any uploaded file from cloud storage
- **File Delete**: Delete files with confirmation from cloud storage
- **Modern UI**: Beautiful, responsive design with animations
- **File Type Support**: Supports various file types (documents, images, videos, archives, etc.)
- **Security**: Secure filename handling and file type validation
- **Global CDN**: Fast file delivery worldwide via Cloudinary's CDN
- **Scalability**: No local storage limits, automatic cloud scaling

## Supported File Types

- Documents: `.txt`, `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`
- Images: `.png`, `.jpg`, `.jpeg`, `.gif`
- Archives: `.zip`, `.rar`
- Media: `.mp3`, `.mp4`, `.avi`, `.mov`

## Installation

1. **Clone or download the project files**

2. **Set up Cloudinary** (see [CLOUDINARY_SETUP.md](CLOUDINARY_SETUP.md) for detailed instructions):
   - Create a Cloudinary account at [cloudinary.com](https://cloudinary.com/)
   - Get your cloud name, API key, and API secret
   - Create a `.env` file with your credentials

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

## Usage

### Uploading Files
1. Click the upload area or drag and drop files onto it
2. Select the file you want to upload
3. The file will be automatically uploaded and appear in the file list

### Downloading Files
1. Click the "Download" button next to any file
2. The file will be downloaded to your default download folder

### Deleting Files
1. Click the "Delete" button next to any file
2. Confirm the deletion in the popup dialog
3. The file will be permanently removed

## Cloud Storage

- All uploaded files are stored securely in Cloudinary cloud storage
- Files are organized in a `file_manager` folder in your Cloudinary account
- Files are automatically optimized and served via global CDN
- No local storage required - everything is in the cloud
- File information (size, modification date) is retrieved from Cloudinary

## Security Features

- Secure filename handling to prevent path traversal attacks
- File type validation to prevent malicious file uploads
- Confirmation dialogs for file deletion
- Input sanitization and validation

## Customization

### Adding New File Types
Edit the `ALLOWED_EXTENSIONS` set in `app.py`:
```python
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar', 'mp3', 'mp4', 'avi', 'mov', 'your_extension'}
```

### Changing Upload Directory
Modify the `UPLOAD_FOLDER` variable in `app.py`:
```python
UPLOAD_FOLDER = 'your_upload_directory'
```

### Styling
The application uses custom CSS with a modern design. You can modify the styles in the `<style>` section of `templates/index.html`.

## API Endpoints

- `GET /` - Main page with file list
- `POST /upload` - Upload a file
- `GET /download/<filename>` - Download a file
- `POST /delete/<filename>` - Delete a file
- `GET /api/files` - Get file list as JSON

## Requirements

- Python 3.7+
- Flask 3.0.2
- Werkzeug 3.0.1
- Cloudinary 1.36.0
- python-dotenv 1.0.0
- requests 2.31.0

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions, please check the console output for error messages or create an issue in the project repository. 