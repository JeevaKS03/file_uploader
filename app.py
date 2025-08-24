from flask import Flask, render_template, send_file, request, redirect, url_for, flash, jsonify
import os
from werkzeug.utils import secure_filename
import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.api
from urllib.parse import urlparse
import requests
from io import BytesIO
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
        
        # Upload to Cloudinary with original filename
        result = cloudinary.uploader.upload(
            file,
            resource_type=app.config['CLOUDINARY_RESOURCE_TYPE'],
            folder=app.config['CLOUDINARY_FOLDER'],
            public_id=final_filename,  # Just the filename, folder will be added automatically
            use_filename=False,  # Don't use Cloudinary's filename generation
            unique_filename=False,  # Don't make unique
            overwrite=False
        )
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
        # List all resources in the configured folder
        result = cloudinary.api.resources(
            type="upload",
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
            # Upload to Cloudinary
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
        # Find the file in Cloudinary by filename
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
            max_results=100
        )
        
        file_url = None
        original_filename = None
        
        for resource in result.get('resources', []):
            if resource.get('original_filename') == filename:
                file_url = resource.get('secure_url')
                original_filename = resource.get('original_filename')
                break
        
        if file_url and original_filename:
            # Download file from Cloudinary
            response = requests.get(file_url)
            if response.status_code == 200:
                # Create BytesIO object from the content
                file_stream = BytesIO(response.content)
                file_stream.seek(0)
                
                return send_file(
                    file_stream,
                    as_attachment=True,
                    download_name=original_filename,
                    mimetype='application/octet-stream'
                )
            else:
                flash('Error downloading file from cloud storage', 'error')
        else:
            flash('File not found in cloud storage', 'error')
            
    except Exception as e:
        print(f"Download error: {e}")
        flash(f'Error downloading file: {str(e)}', 'error')
    
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
        import urllib.parse
        clean_public_id = urllib.parse.unquote(public_id)
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
        result = cloudinary.api.resources(
            type="upload",
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
        print(f"API error: {e}")
        return jsonify({'error': 'Failed to fetch files'}), 500
    
    return jsonify(files)

@app.route('/api/stats')
def api_stats():
    """API endpoint to get file statistics"""
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{app.config['CLOUDINARY_FOLDER']}/",
            max_results=1000
        )
        
        total_files = len(result.get('resources', []))
        total_size = sum(resource.get('bytes', 0) for resource in result.get('resources', []))
        
        # Count recent uploads (last 24 hours)
        recent_count = 0
        current_time = datetime.datetime.now()
        for resource in result.get('resources', []):
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
