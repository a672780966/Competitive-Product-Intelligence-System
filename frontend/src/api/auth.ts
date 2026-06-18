// CPIS V1 — Auth API

import { api } from "./client";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  username: string;
  email: string | null;
  is_active: boolean;
  roles: string[];
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  return api.post<LoginResponse>("/auth/login", data);
}

export async function getMe(): Promise<UserInfo> {
  return api.get<UserInfo>("/auth/me");
}

export function getToken(): string | null {
  return localStorage.getItem("cpis_token");
}

export function setToken(token: string): void {
  localStorage.setItem("cpis_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("cpis_token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
