export interface ApiResponse<T> {
  data: T;
  meta?: Record<string, unknown>;
  error: string | null;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
  error: string | null;
}
