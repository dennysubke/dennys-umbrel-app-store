// ${APP_DATA_DIR}/config/config.js
module.exports = {
  httpUnsafeOrigin: 'https://umbrel-2.local',
  httpSafeOrigin:   'https://umbrel-2.local',
  blockPath: '/cryptpad/block',
  datastorePath: '/cryptpad/datastore',
  filePath: '/cryptpad/files',
  uploadEnabled: true,
  httpAddress: '0.0.0.0',
  httpPort: 3000,
  useSecureTransport: true,
  maxUploadSize: 50 * 1024 * 1024,
};
