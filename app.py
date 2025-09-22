from flask import Flask, render_template, send_file, request, redirect, url_for, flash, jsonify, Response
import os
from werkzeug.utils import secure_filename
import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.api
from urllib.parse import urlparse, unquote
import requests
from io import BytesIO
import mimetypes
from config import config

app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

# Cloudinary Configuration
cloudinary.config(
    cloud_name = app.config['CLOUDINARY_CLOUD_NAME'],
    api_key = app.config['CLOUDINARY_API_KEY'],
    api_secret = app.config['CLOUDINARY_API_SECRET']
)

# Configuration
ALLOWED_EXTENSIONS = app.config['ALLOWED_EXTENSIONS']

# Create uploads directory if it doesn't exist (for temporary storage)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_info(cloudinary_resource):
    """Extract file information from Cloudinary resource"""
    try:
        # Get file size from Cloudinary
        size_bytes = cloudinary_resource.get('bytes', 0)
        
        # Get creation date - handle both Unix timestamp and ISO format
        created_at = cloudinary_resource.get('created_at', '')
        if created_at:
            try:
                # Try to parse as Unix timestamp (integer)
                if isinstance(created_at, (int, str)) and str(created_at).isdigit():
                    created_date = datetime.datetime.fromtimestamp(int(created_at))
                else:
                    # Parse ISO format timestamp
                    created_date = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                modified_date = created_date.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                # Fallback to current time if parsing fails
                modified_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            modified_date = 'Unknown'
        
        return {
            'name': cloudinary_resource.get('original_filename', cloudinary_resource.get('public_id', 'Unknown')),
            'size': size_bytes,
            'modified': modified_date,
            'size_formatted': format_file_size(size_bytes),
            'public_id': cloudinary_resource.get('public_id'),
            'url': cloudinary_resource.get('secure_url'),
            'resource_type': cloudinary_resource.get('resource_type', 'auto')
        }
    except Exception as e:
        print(f"Error processing file info: {e}")
        return None

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_mime_type(filename, content_type=None):
    """Get proper MIME type for file download"""
    # First try to get from content type header
    if content_type and content_type != 'application/octet-stream':
        return content_type
    
    # Get file extension
    file_extension = os.path.splitext(filename)[1].lower()
    
    # Special handling for common file types that might not be detected properly
    mime_type_map = {
        '.pdf': 'application/pdf',
        '.rar': 'application/x-rar-compressed',
        '.zip': 'application/zip',
        '.7z': 'application/x-7z-compressed',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml'
    }
    
    # Check our custom mapping first
    if file_extension in mime_type_map:
        return mime_type_map[file_extension]
    
    # Fallback to Python's mimetypes module
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type
    
    # Default fallback
    return 'application/octet-stream'

def upload_to_cloudinary(file):
    """Upload file to Cloudinary"""
    try:
        # Get the original filename
        original_filename = secure_filename(file.filename)
        
        # Remove file extension to get base name
        base_name, extension = os.path.splitext(original_filename)
        
        # Create a unique filename if it already exists
        counter = 1
        final_filename = original_filename
        
        # Check if file already exists in Cloudinary
        try:
            existing_files = cloudinary.api.resources(
                type="upload",
                prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
                max_results=100
            )
            
            existing_filenames = [resource.get('original_filename') for resource in existing_files.get('resources', [])]
            
            while final_filename in existing_filenames:
                final_filename = f"{base_name}_{counter}{extension}"
                counter += 1
        except:
            # If we can't check existing files, just use original name
            pass
        
        # Keep Cloudinary auto-detection for resource type
        resource_type = 'auto'
        print(f"Uploading {original_filename} as 'auto' resource type to avoid restrictions")
        
        # Upload to Cloudinary with original filename
        print(f"Uploading {original_filename} as {resource_type} resource type")
        
        result = cloudinary.uploader.upload(
            file,
            resource_type=resource_type,
            folder=app.config['CLOUDINARY_FOLDER'],
            public_id=final_filename,  # Just the filename, folder will be added automatically
            use_filename=False,  # Don't use Cloudinary's filename generation
            unique_filename=False,  # Don't make unique
            overwrite=False,
            access_mode='public',  # Make files publicly accessible
            type='upload'  # Ensure it's uploaded as public upload
        )
        print(f"Upload result: {result}")
        return result
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return None

def delete_from_cloudinary(public_id, resource_type="auto"):
    """Delete file from Cloudinary"""
    try:
        print(f"Attempting to delete: {public_id}")
        
        # Try different resource types if auto doesn't work
        resource_types = [resource_type]
        if resource_type == "auto":
            resource_types = ["image", "video", "raw"]
        
        for rt in resource_types:
            try:
                print(f"Trying resource type: {rt}")
                result = cloudinary.uploader.destroy(public_id, resource_type=rt)
                if result.get('result') == 'ok':
                    print(f"Successfully deleted with resource type: {rt}")
                    return True
                else:
                    print(f"Delete failed with resource type {rt}: {result}")
            except Exception as e:
                print(f"Error with resource type {rt}: {e}")
                continue
        
        return False
    except Exception as e:
        print(f"Error deleting from Cloudinary: {e}")
        return False

@app.route('/')
def index():
    # Get list of files from Cloudinary
    files = []
    try:
        # List all resource types in the configured folder
        resource_types = ['image', 'video', 'raw', 'auto']
        
        for resource_type in resource_types:
            try:
                result = cloudinary.api.resources(
                    type="upload",
                    resource_type=resource_type,
                    prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
                    max_results=100,
                    sort_by="created_at",
                    sort_direction="desc"
                )
                
                for resource in result.get('resources', []):
                    file_info = get_file_info(resource)
                    if file_info:
                        files.append(file_info)
            except Exception as e:
                print(f"Error fetching {resource_type} files: {e}")
                continue
                
    except Exception as e:
        print(f"Error fetching files from Cloudinary: {e}")
        flash('Error loading files from cloud storage', 'error')
    
    # Sort files by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        try:
            # Upload all files normally; no disguises
            result = upload_to_cloudinary(file)
            if result:
                filename = result.get('original_filename', file.filename)
                flash(f'File "{filename}" uploaded successfully to cloud!', 'success')
            else:
                flash('Error uploading file to cloud storage', 'error')
        except Exception as e:
            print(f"Upload error: {e}")
            flash('Error uploading file to cloud storage', 'error')
    else:
        flash('File type not allowed. Please upload a valid file.', 'error')
    
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Find the file in Cloudinary by filename across all resource types
        resource_types = ['image', 'video', 'raw', 'auto']
        file_url = None
        original_filename = None
        
        for resource_type in resource_types:
            try:
                result = cloudinary.api.resources(
                    type="upload",
                    resource_type=resource_type,
                    prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
                    max_results=100
                )
                
                for resource in result.get('resources', []):
                    # Try multiple ways to match the filename
                    resource_filename = resource.get('original_filename') or resource.get('public_id', '').split('/')[-1]
                    if resource_filename == filename:
                        file_url = resource.get('secure_url')
                        original_filename = resource_filename
                        
                        # For raw files, generate a signed URL for secure access
                        if resource_type == 'raw':
                            from cloudinary import utils as cloudinary_utils
                            public_id = resource.get('public_id')
                            
                            # Generate a signed URL for secure access to raw files
                            signed_url, options = cloudinary_utils.cloudinary_url(
                                public_id,
                                resource_type='raw',
                                type='upload',
                                sign_url=True,
                                secure=True,
                                version=resource.get('version')
                            )
                            print(f"Generated signed download URL: {signed_url}")
                            file_url = signed_url
                        
                        break
                
                if file_url and original_filename:
                    break
            except Exception as e:
                print(f"Error searching {resource_type} files: {e}")
                continue
        
        if file_url and original_filename:
            # Redirect to Cloudinary's signed attachment URL for reliable downloads
            from cloudinary import utils as cloudinary_utils
            signed_url, _ = cloudinary_utils.cloudinary_url(
                resource.get('public_id'),
                resource_type=resource.get('resource_type', 'auto'),
                type='upload',
                sign_url=True,
                secure=True,
                attachment=original_filename
            )
            return redirect(signed_url)
        else:
            flash('File not found in cloud storage', 'error')
            
    except Exception as e:
        print(f"Download error: {e}")
        flash(f'Error downloading file: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/download_by_id/<path:public_id>')
def download_file_by_id(public_id):
    """Download file directly using Cloudinary public_id - more reliable"""
    try:
        # Clean the public_id
        clean_public_id = unquote(public_id)
        print(f"Downloading file with public_id: {clean_public_id}")
        
        # Try to get file info from Cloudinary and redirect to signed attachment URL
        resource_types = ['image', 'video', 'raw', 'auto']
        for rt in resource_types:
            try:
                result = cloudinary.api.resource(clean_public_id, resource_type=rt)
                if result and result.get('public_id'):
                    original_filename = result.get('original_filename') or clean_public_id.split('/')[-1]
                    from cloudinary import utils as cloudinary_utils
                    signed_url, _ = cloudinary_utils.cloudinary_url(
                        result.get('public_id'),
                        resource_type=rt,
                        type='upload',
                        sign_url=True,
                        secure=True,
                        attachment=original_filename
                    )
                    print(f"Redirecting to signed attachment URL for {original_filename}")
                    return redirect(signed_url)
            except Exception as e:
                print(f"Error with resource type {rt}: {e}")
                continue
        flash('File not found in cloud storage', 'error')
            
    except Exception as e:
        print(f"Download by ID error: {e}")
        flash(f'Error downloading file: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/download_archive/<path:public_id>')
def download_file_archive(public_id):
    """Alternative download using archive method - should work for restricted files"""
    try:
        import zipfile
        import io
        import cloudinary.utils
        
        # Clean the public_id
        clean_public_id = unquote(public_id)
        print(f"Archive download for: {clean_public_id}")
        
        # Get file info first
        resource_types = ['image', 'video', 'raw']
        original_filename = None
        resource_type = None
        
        for rt in resource_types:
            try:
                result = cloudinary.api.resource(clean_public_id, resource_type=rt)
                if result:
                    original_filename = result.get('original_filename') or clean_public_id.split('/')[-1]
                    resource_type = rt
                    print(f"Found: {original_filename} as {rt}")
                    break
            except:
                continue
        
        if not original_filename:
            flash('File not found', 'error')
            return redirect(url_for('index'))
        
        # Use Cloudinary Admin API to get file content directly
        try:
            # Method: Use Admin API with basic authentication
            admin_url = f"https://api.cloudinary.com/v1_1/{app.config['CLOUDINARY_CLOUD_NAME']}/resources/{resource_type}/upload/{clean_public_id}"
            
            print(f"Admin API URL: {admin_url}")
            
            # Use basic auth with API credentials
            import base64
            credentials = base64.b64encode(f"{app.config['CLOUDINARY_API_KEY']}:{app.config['CLOUDINARY_API_SECRET']}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json'
            }
            
            # Get resource info
            admin_response = requests.get(admin_url, headers=headers)
            print(f"Admin API status: {admin_response.status_code}")
            
            if admin_response.status_code == 200:
                resource_data = admin_response.json()
                secure_url = resource_data.get('secure_url')
                print(f"Got secure URL: {secure_url}")
                
                # Now try to download the file using the secure URL with authentication
                download_response = requests.get(secure_url, headers=headers, timeout=30)
                print(f"Download status: {download_response.status_code}")
                print(f"Content-Type: {download_response.headers.get('content-type')}")
                print(f"Content-Length: {download_response.headers.get('content-length')}")
                
                if download_response.status_code == 200:
                    file_content = download_response.content
                    print(f"Downloaded {len(file_content)} bytes successfully!")
                    
                    # Return the file
                    mime_type = get_mime_type(original_filename)
                    return Response(
                        file_content,
                        mimetype=mime_type,
                        headers={
                            'Content-Disposition': f'attachment; filename="{original_filename}"',
                            'Content-Length': str(len(file_content))
                        }
                    )
                else:
                    print(f"Direct download failed: {download_response.status_code}")
            else:
                print(f"Admin API failed: {admin_response.status_code}")
                print(f"Response: {admin_response.text}")
                
        except Exception as e:
            print(f"Admin API method failed: {e}")
        
        # Fallback: Try the archive method with corrected signature
        try:
            print("Trying fallback archive method...")
            # Use a simpler approach - try without signature first
            simple_archive_url = f"https://api.cloudinary.com/v1_1/{app.config['CLOUDINARY_CLOUD_NAME']}/image/generate_archive"
            simple_archive_url += f"?public_ids={clean_public_id}&resource_type={resource_type}&mode=download&target_format=zip"
            
            # Try with basic auth
            import base64
            credentials = base64.b64encode(f"{app.config['CLOUDINARY_API_KEY']}:{app.config['CLOUDINARY_API_SECRET']}".encode()).decode()
            headers = {'Authorization': f'Basic {credentials}'}
            
            response = requests.get(simple_archive_url, headers=headers, timeout=30)
            print(f"Simple archive status: {response.status_code}")
            
            if response.status_code == 200:
                # Extract file from zip
                import zipfile
                import io
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                    files = zip_file.namelist()
                    if files:
                        file_content = zip_file.read(files[0])
                        print(f"Extracted {len(file_content)} bytes from archive")
                        
                        # Return the file
                        mime_type = get_mime_type(original_filename)
                        return Response(
                            file_content,
                            mimetype=mime_type,
                            headers={
                                'Content-Disposition': f'attachment; filename="{original_filename}"',
                                'Content-Length': str(len(file_content))
                            }
                        )
        except Exception as e:
            print(f"Archive fallback failed: {e}")
        
        flash('Download failed', 'error')
        
    except Exception as e:
        print(f"Archive download error: {e}")
        flash(f'Download error: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/download_zip/<path:public_id>')
def download_zip_file(public_id):
    """Special download route just for ZIP files - handles disguised filenames"""
    try:
        clean_public_id = unquote(public_id)
        print(f"ZIP download for: {clean_public_id}")
        
        # For disguised ZIP files, try looking for .txt version
        if clean_public_id.endswith('.zip'):
            txt_public_id = clean_public_id.replace('.zip', '.txt')
            print(f"Looking for disguised ZIP as: {txt_public_id}")
        else:
            txt_public_id = clean_public_id
        
        # Search for the file (might be disguised as .txt)
        resource_types = ['raw', 'auto', 'image', 'video']
        file_url = None
        original_filename = clean_public_id.split('/')[-1]  # Use the original ZIP name
        
        for rt in resource_types:
            try:
                # Try both the original public_id and the .txt version
                for pid in [clean_public_id, txt_public_id]:
                    try:
                        result = cloudinary.api.resource(pid, resource_type=rt)
                        if result:
                            file_url = result.get('secure_url')
                            print(f"Found disguised ZIP: {pid} with URL: {file_url}")
                            break
                    except:
                        continue
                if file_url:
                    break
            except:
                continue
        
        if file_url:
            print(f"Downloading disguised ZIP from: {file_url}")
            
            # Download the file (it's stored as .txt but contains ZIP data)
            response = requests.get(file_url, stream=True, timeout=30)
            print(f"ZIP response status: {response.status_code}")
            print(f"Original filename will be: {original_filename}")
            
            if response.status_code == 200:
                # Ensure original_filename ends with .zip
                if not original_filename.endswith('.zip'):
                    original_filename = original_filename + '.zip'
                
                print(f"Serving file as: {original_filename}")
                
                # Return as ZIP file with correct filename and strong headers
                def generate():
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                
                return Response(
                    generate(),
                    mimetype='application/zip',
                    headers={
                        'Content-Disposition': f'attachment; filename="{original_filename}"',
                        'Content-Type': 'application/zip',
                        'Content-Length': response.headers.get('content-length', ''),
                        'Cache-Control': 'no-cache',
                        'X-Content-Type-Options': 'nosniff'
                    }
                )
            else:
                flash(f'ZIP download failed with status: {response.status_code}', 'error')
        else:
            flash('ZIP file not found', 'error')
            
    except Exception as e:
        print(f"ZIP download error: {e}")
        flash(f'ZIP download error: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        print(f"Attempting to delete file: {filename}")
        
        # Find the file in Cloudinary by filename
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
            max_results=100
        )
        
        public_id = None
        resource_type = "auto"
        original_filename = None
        
        # Debug: print all resources to see what we're working with
        print(f"Found {len(result.get('resources', []))} resources")
        for resource in result.get('resources', []):
            print(f"Resource: {resource.get('original_filename')} vs {filename}")
            if resource.get('original_filename') == filename:
                public_id = resource.get('public_id')
                resource_type = resource.get('resource_type', 'auto')
                original_filename = resource.get('original_filename')
                print(f"Found matching file: {original_filename} with public_id: {public_id}")
                break
        
        if public_id and original_filename:
            # Delete from Cloudinary
            print(f"Deleting from Cloudinary: {public_id}")
            if delete_from_cloudinary(public_id, resource_type):
                flash(f'File "{original_filename}" deleted successfully from cloud!', 'success')
            else:
                flash('Error deleting file from cloud storage', 'error')
        else:
            flash(f'File "{filename}" not found in cloud storage', 'error')
            
    except Exception as e:
        print(f"Delete error: {e}")
        flash(f'Error deleting file: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete_by_id/<path:public_id>', methods=['POST'])
def delete_file_by_id(public_id):
    """Delete file by Cloudinary public ID"""
    try:
        print(f"Attempting to delete file by ID: {public_id}")
        
        # Clean the public_id - remove any URL encoding
        clean_public_id = unquote(public_id)
        print(f"Cleaned public_id: {clean_public_id}")
        
        # Delete from Cloudinary directly using public ID
        if delete_from_cloudinary(clean_public_id, "auto"):
            flash(f'File deleted successfully from cloud!', 'success')
        else:
            flash('Error deleting file from cloud storage', 'error')
            
    except Exception as e:
        print(f"Delete by ID error: {e}")
        flash(f'Error deleting file: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/debug/files')
def debug_files():
    """Debug route to see file information"""
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
            max_results=100
        )
        
        debug_info = []
        for resource in result.get('resources', []):
            debug_info.append({
                'public_id': resource.get('public_id'),
                'original_filename': resource.get('original_filename'),
                'secure_url': resource.get('secure_url'),
                'created_at': resource.get('created_at')
            })
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files')
def api_files():
    """API endpoint to get file list as JSON"""
    files = []
    try:
        # List all resource types in the configured folder
        resource_types = ['image', 'video', 'raw']
        
        for resource_type in resource_types:
            try:
                result = cloudinary.api.resources(
                    type="upload",
                    resource_type=resource_type,
                    prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
                    max_results=100,
                    sort_by="created_at",
                    sort_direction="desc"
                )
                
                for resource in result.get('resources', []):
                    file_info = get_file_info(resource)
                    if file_info:
                        files.append(file_info)
            except Exception as e:
                print(f"Error fetching {resource_type} files for API: {e}")
                continue
                
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Failed to fetch files'}), 500
    
    return jsonify(files)

@app.route('/api/stats')
def api_stats():
    """API endpoint to get file statistics"""
    try:
        # List all resource types in the configured folder
        resource_types = ['image', 'video', 'raw']
        all_resources = []
        
        for resource_type in resource_types:
            try:
                result = cloudinary.api.resources(
                    type="upload",
                    resource_type=resource_type,
                    prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
                    max_results=1000
                )
                all_resources.extend(result.get('resources', []))
            except Exception as e:
                print(f"Error fetching {resource_type} files for stats: {e}")
                continue
        
        total_files = len(all_resources)
        total_size = sum(resource.get('bytes', 0) for resource in all_resources)
        
        # Count recent uploads (last 24 hours)
        recent_count = 0
        current_time = datetime.datetime.now()
        for resource in all_resources:
            created_at = resource.get('created_at')
            if created_at:
                try:
                    # Try to parse as Unix timestamp (integer)
                    if isinstance(created_at, (int, str)) and str(created_at).isdigit():
                        created_date = datetime.datetime.fromtimestamp(int(created_at))
                    else:
                        # Parse ISO format timestamp
                        created_date = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if (current_time - created_date).days < 1:
                        recent_count += 1
                except (ValueError, TypeError):
                    # Skip if parsing fails
                    continue
        
        return jsonify({
            'total_files': total_files,
            'total_size': format_file_size(total_size),
            'total_size_bytes': total_size,
            'recent_uploads': recent_count
        })
        
    except Exception as e:
        print(f"Stats API error: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
