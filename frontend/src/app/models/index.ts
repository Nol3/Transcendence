/* Interface definitions for type safety */

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  profile: UserProfile;
}

export interface UserProfile {
  id: number;
  bio: string;
  avatar: string;
  win_count: number;
  loss_count: number;
  elo_rating: number;
  is_online: boolean;
}

export interface Game {
  id: number;
  player1: User;
  player2: User;
  winner: User | null;
  status: 'pending' | 'in_progress' | 'finished';
  player1_score: number;
  player2_score: number;
  played_at: string;
  finished_at: string | null;
}

export interface Message {
  id: number;
  sender: User;
  recipient: User;
  content: string;
  created_at: string;
  is_read: boolean;
}

export interface Tournament {
  id: number;
  name: string;
  description: string;
  creator: User;
  max_players: number;
  status: 'pending' | 'in_progress' | 'finished';
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  participants: TournamentParticipant[];
}

export interface TournamentParticipant {
  id: number;
  user: User;
  joined_at: string;
}
