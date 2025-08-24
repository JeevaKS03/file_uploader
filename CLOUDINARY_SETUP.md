# Cloudinary Setup Guide

This guide will help you set up Cloudinary integration for your file manager application.

## Step 1: Create a Cloudinary Account

1. Go to [Cloudinary](https://cloudinary.com/) and sign up for a free account
2. Verify your email address
3. Log in to your Cloudinary dashboard

## Step 2: Get Your Cloudinary Credentials

1. In your Cloudinary dashboard, go to the **Account Details** section
2. Copy the following information:
   - **Cloud Name** (e.g., `mycloud123`)
   - **API Key** (e.g., `123456789012345`)
   - **API Secret** (e.g., `abcdefghijklmnopqrstuvwxyz`)

## Step 3: Configure Your Application

### Option 1: Using Environment Variables (Recommended)

1. Create a `.env` file in your project root:
```bash
# Flask Configuration
SECRET_KEY=your-super-secret-key-here

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Flask Environment
FLASK_CONFIG=development
```

2. Replace the placeholder values with your actual Cloudinary credentials

### Option 2: Direct Configuration

If you prefer to configure directly in the code, edit `config.py`:

```python
class Config:
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME = 'your_cloud_name'  # Replace with your cloud name
    CLOUDINARY_API_KEY = 'your_api_key'        # Replace with your API key
    CLOUDINARY_API_SECRET = 'your_api_secret'  # Replace with your API secret
```

## Step 4: Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

## Step 5: Test Your Setup

1. Run your application:
```bash
python app.py
```

2. Open your browser and go to `http://localhost:5000`
3. Try uploading a file to test the Cloudinary integration

## Step 6: Verify Upload

1. Go to your Cloudinary dashboard
2. Navigate to the **Media Library**
3. You should see a `file_manager` folder with your uploaded files

## Features of Cloudinary Integration

### ✅ **Cloud Storage**
- All files are stored securely in Cloudinary's cloud
- No local storage required
- Automatic backup and redundancy

### ✅ **Global CDN**
- Files are served from Cloudinary's global CDN
- Fast download speeds worldwide
- Automatic optimization

### ✅ **File Organization**
- Files are organized in a `file_manager` folder
- Automatic file naming and deduplication
- Original filenames preserved

### ✅ **Security**
- Secure HTTPS URLs for all files
- API key authentication
- Access control and permissions

### ✅ **Scalability**
- No storage limits (within your plan)
- Automatic scaling
- No server storage concerns

## Troubleshooting

### Common Issues:

1. **"Invalid credentials" error**
   - Double-check your Cloudinary credentials
   - Ensure your account is active

2. **"Upload failed" error**
   - Check your internet connection
   - Verify file size limits
   - Ensure file type is allowed

3. **"File not found" error**
   - Check if the file exists in Cloudinary dashboard
   - Verify the folder structure

### Support:

- [Cloudinary Documentation](https://cloudinary.com/documentation)
- [Cloudinary Support](https://support.cloudinary.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit your `.env` file to version control**
2. **Keep your API secret secure**
3. **Use environment variables in production**
4. **Regularly rotate your API keys**
5. **Monitor your Cloudinary usage**

## Production Deployment

For production deployment:

1. Set `FLASK_CONFIG=production` in your environment
2. Use a strong `SECRET_KEY`
3. Configure proper logging
4. Set up monitoring for Cloudinary usage
5. Consider using Cloudinary's webhook notifications

## Cost Considerations

Cloudinary offers a generous free tier:
- 25 GB storage
- 25 GB bandwidth per month
- 25,000 transformations per month

For higher usage, consider their paid plans based on your needs. 