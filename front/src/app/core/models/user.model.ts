export interface UserProfile {
  id?: number;
  bio?: string;
  avatar?: string | null;
  win_count?: number;
  loss_count?: number;
  elo_rating?: number;
  is_online?: boolean;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  profile?: UserProfile;
  createdAt?: string;
  wins?: number;
  losses?: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}
