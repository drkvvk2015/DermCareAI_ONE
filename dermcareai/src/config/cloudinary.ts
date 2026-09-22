import { Cloudinary } from '@cloudinary/url-gen';
import { CLOUDINARY_CLOUD_NAME } from '@env';

export const getImageUrl = (publicId: string) => {
  if (!CLOUDINARY_CLOUD_NAME) {
    throw new Error('Cloudinary cloud name is not configured');
  }
  const cloudinary = new Cloudinary({
    cloud: { cloudName: CLOUDINARY_CLOUD_NAME },
  });
  return cloudinary.image(publicId).toURL();
};

// Uploads are intentionally implemented by the authenticated service layer,
// which obtains short-lived server-signed parameters. No API secret is ever
// read by this mobile configuration module.
export { uploadImage } from '../services/cloudinary';
