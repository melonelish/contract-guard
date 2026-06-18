export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  meta?: {
    page?: number;
    page_size?: number;
    total?: number;
  };
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
}

export interface AuthPayload {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Contract {
  id: string;
  title: string | null;
  file_url: string;
  file_type: string;
  file_size: number | null;
  contract_type: string | null;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface ContractDetail extends Contract {
  tenant_id: string;
  user_id: string;
  page_count: number | null;
}
