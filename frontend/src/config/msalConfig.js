/**
 * MSAL (Microsoft Authentication Library) Configuration
 * For Azure AD SSO integration
 */

// MSAL configuration - these values are loaded from backend /auth/sso/config
export const getMsalConfig = (ssoConfig) => {
  if (!ssoConfig?.enabled) {
    return null;
  }

  return {
    auth: {
      clientId: ssoConfig.client_id,
      authority: ssoConfig.authority,
      redirectUri: window.location.origin,
      postLogoutRedirectUri: window.location.origin,
      navigateToLoginRequestUrl: true,
    },
    cache: {
      cacheLocation: "sessionStorage",
      storeAuthStateInCookie: false,
    },
    system: {
      loggerOptions: {
        loggerCallback: (level, message, containsPii) => {
          if (containsPii) return;
          switch (level) {
            case 0: // Error
              console.error(message);
              break;
            case 1: // Warning
              console.warn(message);
              break;
            case 2: // Info
              console.info(message);
              break;
            case 3: // Verbose
              console.debug(message);
              break;
            default:
              break;
          }
        },
        logLevel: 1, // Warning
      },
    },
  };
};

// Login request scopes
export const getLoginRequest = (ssoConfig) => ({
  scopes: ssoConfig?.scopes || ["openid", "profile", "email"],
});

// Token request for API access
export const getTokenRequest = (ssoConfig) => ({
  scopes: ssoConfig?.scopes || ["openid", "profile", "email"],
});
