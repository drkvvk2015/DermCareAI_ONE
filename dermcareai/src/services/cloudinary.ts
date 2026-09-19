import { Cloudinary } from '@cloudinary/url-gen';
import { API_URL } from '@env';
import { auth } from '../config/firebase';

type SignedUpload = {
  cloud_name: string;
  api_key: string;
  timestamp: number;
  signature: string;
  upload_preset: string;
  folder: string;
  resource_type: string;
};

async function getSignedUpload(subjectId: string, purpose: string): Promise<SignedUpload> {
  const user = auth.currentUser;
  if (!user) throw new Error('Authentication required. Please sign in again.');
  const token = await user.getIdToken();
  const response = await fetch(`${API_URL}/media/sign-upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ subject_id: subjectId, purpose }),
  });
  const body = await response.text();
  if (!response.ok) throw new Error(body || `Upload authorization failed: ${response.status}`);
  return JSON.parse(body) as SignedUpload;
}

async function uploadFile(filePart: any, subjectId: string, purpose: string): Promise<string> {
  const signed = await getSignedUpload(subjectId, purpose);
  const formData = new FormData();
  formData.append('file', filePart);
  formData.append('api_key', signed.api_key);
  formData.append('timestamp', String(signed.timestamp));
  formData.append('signature', signed.signature);
  formData.append('upload_preset', signed.upload_preset);
  formData.append('folder', signed.folder);
  const response = await fetch(`https://api.cloudinary.com/v1_1/${signed.cloud_name}/${signed.resource_type}/upload`, { method: 'POST', body: formData, headers: { Accept: 'application/json' } });
  const body = await response.text();
  if (!response.ok) throw new Error(body || 'Clinical image upload failed');
  const data = JSON.parse(body);
  if (!data.secure_url) throw new Error('Cloudinary did not return a secure URL');
  return data.secure_url as string;
}

export const uploadImage = async (imageUri: string, subjectId: string, purpose = 'clinical-image'): Promise<string> => {
  return uploadFile(
    { uri: imageUri, type: 'image/jpeg', name: imageUri.split('/').pop() || 'clinical-image.jpg' } as any,
    subjectId,
    purpose,
  );
};

export const uploadDataUri = async (dataUri: string, subjectId: string, purpose = 'clinical-artifact'): Promise<string> => {
  if (!dataUri.startsWith('data:')) throw new Error('Expected a data URI');
  return uploadFile(dataUri, subjectId, purpose);
};

export const getImageUrl = (cloudName: string, publicId: string) => {
  const cloudinary = new Cloudinary({ cloud: { cloudName } });
  return cloudinary.image(publicId).toURL();
};
