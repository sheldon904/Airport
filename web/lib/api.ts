import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';
import type {
  TokenResponse,
  User,
  Transaction,
  TransactionDetail,
  TransactionListResponse,
  Document,
  ExtractedData,
  Deadline,
  UpcomingDeadline,
  DashboardData,
  CreateTransactionForm,
  CreateDeadlineForm,
  PropertyAddress,
  TransactionSummaryReport,
  OrganizationOverviewReport,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

// Cookie configuration with security flags
const COOKIE_OPTIONS: Cookies.CookieAttributes = {
  // Note: httpOnly can only be set by the server, not JavaScript
  // For production, tokens should be set via Set-Cookie headers from the backend
  secure: process.env.NODE_ENV === 'production', // Only send over HTTPS in production
  sameSite: 'strict', // Prevent CSRF attacks
  path: '/',
};

// API Error interface for proper typing (NEW-018 fix)
interface ApiError {
  response?: {
    status: number;
    data?: {
      detail?: string;
      message?: string;
    };
  };
  message: string;
}

// Type guard for API errors
function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error
  );
}

// Extract error message from API error
export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred'
    );
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
}

class ApiClient {
  private client: AxiosInstance;
  // Store tokens in memory for added security (reduces exposure window)
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      // Include CSRF token if available
      xsrfCookieName: 'csrf_token',
      xsrfHeaderName: 'X-CSRF-Token',
    });

    // Initialize tokens from cookies on startup
    this.accessToken = Cookies.get('access_token') || null;
    this.refreshToken = Cookies.get('refresh_token') || null;

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = this.accessToken || Cookies.get('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle token refresh on 401
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
          originalRequest._retry = true;

          const refresh = this.refreshToken || Cookies.get('refresh_token');
          if (refresh) {
            try {
              const response = await this.refreshTokens(refresh);
              this.setTokens(response);
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${response.access_token}`;
              }
              return this.client(originalRequest);
            } catch {
              this.clearTokens();
              if (typeof window !== 'undefined') {
                window.location.href = '/auth/login';
              }
            }
          } else {
            this.clearTokens();
            if (typeof window !== 'undefined') {
              window.location.href = '/auth/login';
            }
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // Token management with security flags (NEW-004 fix)
  setTokens(tokens: TokenResponse) {
    // Store in memory first (more secure)
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;

    // Also store in cookies for persistence across page loads
    // Using secure flags to minimize exposure
    Cookies.set('access_token', tokens.access_token, {
      ...COOKIE_OPTIONS,
      expires: 1, // 1 day
    });
    Cookies.set('refresh_token', tokens.refresh_token, {
      ...COOKIE_OPTIONS,
      expires: 7, // 7 days
    });
  }

  clearTokens() {
    // Clear memory
    this.accessToken = null;
    this.refreshToken = null;

    // Clear cookies
    Cookies.remove('access_token', { path: '/' });
    Cookies.remove('refresh_token', { path: '/' });
  }

  getAccessToken(): string | null {
    return this.accessToken || Cookies.get('access_token') || null;
  }

  isAuthenticated(): boolean {
    return this.getAccessToken() !== null;
  }

  // Auth endpoints
  async register(data: {
    organization_name: string;
    admin_email: string;
    admin_password: string;
    admin_name: string;
    license_number?: string;
    state?: string;
  }) {
    const response = await this.client.post('/api/v1/auth/register', data);
    return response.data;
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await this.client.post('/api/v1/auth/login', {
      email,
      password,
    });
    return response.data;
  }

  async refreshTokens(refreshToken: string): Promise<TokenResponse> {
    const response = await this.client.post('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/api/v1/auth/me');
    return response.data;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.client.post('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  async requestPasswordReset(email: string): Promise<void> {
    await this.client.post('/api/v1/auth/forgot-password', { email });
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await this.client.post('/api/v1/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  }

  // Dashboard
  async getDashboard(): Promise<DashboardData> {
    const response = await this.client.get('/api/v1/transactions/dashboard');
    return response.data;
  }

  // Transactions
  async listTransactions(
    page = 1,
    pageSize = 20,
    status?: string
  ): Promise<TransactionListResponse> {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (status) params.status = status;
    const response = await this.client.get('/api/v1/transactions', { params });
    return response.data;
  }

  async getTransaction(id: string): Promise<TransactionDetail> {
    const response = await this.client.get(`/api/v1/transactions/${id}`);
    return response.data;
  }

  async createTransaction(data: CreateTransactionForm): Promise<Transaction> {
    const response = await this.client.post('/api/v1/transactions', data);
    return response.data;
  }

  async updateTransaction(
    id: string,
    data: Partial<{
      status: string;
      purchase_price: number;
      effective_date: string;
      closing_date: string;
      notes: string;
    }>
  ): Promise<Transaction> {
    const response = await this.client.patch(`/api/v1/transactions/${id}`, data);
    return response.data;
  }

  async deleteTransaction(id: string): Promise<void> {
    await this.client.delete(`/api/v1/transactions/${id}`);
  }

  async addParty(transactionId: string, party: Omit<import('@/types').Party, 'id'>): Promise<Transaction> {
    const response = await this.client.post(`/api/v1/transactions/${transactionId}/parties`, {
      party,
    });
    return response.data;
  }

  async removeParty(transactionId: string, partyId: string): Promise<Transaction> {
    const response = await this.client.delete(
      `/api/v1/transactions/${transactionId}/parties/${partyId}`
    );
    return response.data;
  }

  // Documents
  async listDocuments(
    transactionId: string,
    documentType?: string,
    status?: string
  ): Promise<Document[]> {
    const params: Record<string, string> = {};
    if (documentType) params.document_type = documentType;
    if (status) params.status_filter = status;
    const response = await this.client.get(
      `/api/v1/documents/transaction/${transactionId}`,
      { params }
    );
    return response.data;
  }

  async getDocument(id: string): Promise<Document> {
    const response = await this.client.get(`/api/v1/documents/${id}`);
    return response.data;
  }

  async uploadDocument(
    transactionId: string,
    file: File,
    documentType?: string
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    if (documentType) formData.append('document_type', documentType);

    const response = await this.client.post(
      `/api/v1/documents/upload/${transactionId}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  async getDocumentDownloadUrl(id: string): Promise<{ url: string; expires_in: number }> {
    const response = await this.client.get(`/api/v1/documents/${id}/download`);
    return response.data;
  }

  async getExtractedData(id: string): Promise<ExtractedData> {
    const response = await this.client.get(`/api/v1/documents/${id}/extracted`);
    return response.data;
  }

  async verifyDocument(
    id: string,
    corrections?: Record<string, unknown>
  ): Promise<Document> {
    const response = await this.client.post(`/api/v1/documents/${id}/verify`, {
      corrections,
    });
    return response.data;
  }

  async reprocessDocument(id: string): Promise<Document> {
    const response = await this.client.post(`/api/v1/documents/${id}/reprocess`);
    return response.data;
  }

  async deleteDocument(id: string): Promise<void> {
    await this.client.delete(`/api/v1/documents/${id}`);
  }

  async getReviewQueue(): Promise<Document[]> {
    const response = await this.client.get('/api/v1/documents/review-queue');
    return response.data;
  }

  // Deadlines
  async listDeadlines(
    transactionId: string,
    includeCompleted = false
  ): Promise<Deadline[]> {
    const response = await this.client.get(
      `/api/v1/deadlines/transaction/${transactionId}`,
      { params: { include_completed: includeCompleted } }
    );
    return response.data;
  }

  async getDeadline(id: string): Promise<Deadline> {
    const response = await this.client.get(`/api/v1/deadlines/${id}`);
    return response.data;
  }

  async getUpcomingDeadlines(daysAhead = 7): Promise<UpcomingDeadline[]> {
    const response = await this.client.get('/api/v1/deadlines/upcoming', {
      params: { days_ahead: daysAhead },
    });
    return response.data;
  }

  async getOverdueDeadlines(): Promise<Deadline[]> {
    const response = await this.client.get('/api/v1/deadlines/overdue');
    return response.data;
  }

  async createDeadline(data: CreateDeadlineForm): Promise<Deadline> {
    const response = await this.client.post('/api/v1/deadlines', data);
    return response.data;
  }

  async updateDeadline(
    id: string,
    data: { due_date?: string; name?: string; notes?: string }
  ): Promise<Deadline> {
    const response = await this.client.patch(`/api/v1/deadlines/${id}`, data);
    return response.data;
  }

  async completeDeadline(id: string, notes?: string): Promise<Deadline> {
    const response = await this.client.post(`/api/v1/deadlines/${id}/complete`, {
      notes,
    });
    return response.data;
  }

  async waiveDeadline(id: string, reason: string): Promise<Deadline> {
    const response = await this.client.post(`/api/v1/deadlines/${id}/waive`, {
      reason,
    });
    return response.data;
  }

  async extendDeadline(
    id: string,
    newDate: string,
    reason?: string
  ): Promise<Deadline> {
    const response = await this.client.post(`/api/v1/deadlines/${id}/extend`, {
      new_date: newDate,
      reason,
    });
    return response.data;
  }

  async deleteDeadline(id: string): Promise<void> {
    await this.client.delete(`/api/v1/deadlines/${id}`);
  }

  // Reports
  async getTransactionReport(
    transactionId: string,
    format: 'json' | 'html' = 'json'
  ): Promise<TransactionSummaryReport> {
    const response = await this.client.post(
      `/api/v1/reports/transactions/${transactionId}`,
      null,
      { params: { format } }
    );
    return response.data;
  }

  async downloadTransactionReport(transactionId: string): Promise<Blob> {
    const response = await this.client.get(
      `/api/v1/reports/transactions/${transactionId}/download`,
      { responseType: 'blob' }
    );
    return response.data;
  }

  async getOrganizationReport(): Promise<OrganizationOverviewReport> {
    const response = await this.client.get('/api/v1/reports/organization');
    return response.data;
  }

  async getDashboardMetrics(): Promise<DashboardData> {
    const response = await this.client.get('/api/v1/reports/dashboard');
    return response.data;
  }
}

export const api = new ApiClient();
