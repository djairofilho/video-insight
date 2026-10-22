/** Auth0 Action: Login / Post Login. Publique e adicione ao fluxo no painel. */
exports.onExecutePostLogin = async (event, api) => {
  if (event.client.client_id !== 'ni2qNMV1N9PYkxUOqUNaIC5vbgF28BsJ') return;
  if (typeof event.user.username === 'string' && event.user.username.trim()) {
    api.idToken.setCustomClaim('https://video-insight-api/username', event.user.username);
  }
};
