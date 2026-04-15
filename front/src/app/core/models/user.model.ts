export interface User {
  id: number;
  username: string;
  email: string;
  avatar?: string;
  createdAt: string;
  wins: number;
  losses: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}
