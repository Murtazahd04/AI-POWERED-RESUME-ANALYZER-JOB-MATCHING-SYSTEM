import React, { useState } from 'react';
import api from '../services/api';

const FileUpload = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedUrl, setUploadedUrl] = useState('');
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    // FIX: Grab the single file object [0] instead of the whole file list array layout!
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file first.');
      return;
    }

    // Append the file buffer to the multipart form stream data block
    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploading(true);
      setError('');
      
      // Make the POST request to your FastAPI backend
      const response = await api.post('/media/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Secure link pointer retrieved out of Cloudinary via FastAPI configuration
      setUploadedUrl(response.data.file_url);
    } catch (err) {
      console.error(err);
      setError('Upload failed. Ensure backend server is running and .env keys are correct.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '8px', maxWidth: '400px' }}>
      <h3>Cloudinary Asset Uploader</h3>
      <form onSubmit={handleUpload}>
        <input type="file" onChange={handleFileChange} accept="image/*" />
        <button type="submit" disabled={uploading} style={{ marginLeft: '10px' }}>
          {uploading ? 'Uploading...' : 'Upload to Cloud'}
        </button>
      </form>

      {error && <p style={{ color: 'red', marginTop: '10px' }}>{error}</p>}

      {uploadedUrl && (
        <div style={{ marginTop: '20px' }}>
          <p style={{ color: 'green' }}>🎉 Upload Successful!</p>
          <a href={uploadedUrl} target="_blank" rel="noopener noreferrer">View Hosted File Link</a>
          <div style={{ marginTop: '10px' }}>
            <img src={uploadedUrl} alt="Uploaded preview" style={{ maxWidth: '100%', borderRadius: '4px' }} />
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
