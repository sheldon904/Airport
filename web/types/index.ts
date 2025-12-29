// API Response Types

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
}

export interface Organization {
  id: string;
  name: string;
  state: string;
  subscription_tier: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface PropertyAddress {
  street: string;
  unit?: string;
  city: string;
  state: string;
  zip_code: string;
  county?: string;
}

export interface Party {
  id?: string;
  role: string;
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  license_number?: string;
}

export interface ChecklistItem {
  id: string;
  name: string;
  description?: string;
  category: string;
  required: boolean;
  status: string;
  document_id?: string;
}

export interface Transaction {
  id: string;
  status: string;
  transaction_type: string;
  property_address: PropertyAddress;
  purchase_price?: number;
  year_built?: number;
  effective_date?: string;
  closing_date?: string;
  parties: Party[];
  notes?: string;
  created_at: string;
  updated_at: string;
  buyer_name?: string;
  seller_name?: string;
  checklist?: Record<string, boolean>;
}

export interface TransactionDetail extends Transaction {
  documents_count: number;
  deadlines_count: number;
  checklist_completion: number;
  checklist_items: ChecklistItem[];
  upcoming_deadlines: DeadlineSummary[];
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
}

export interface Document {
  id: string;
  transaction_id: string;
  document_type: string;
  filename: string;
  content_type: string;
  file_size?: number;
  status: string;
  extraction_status: string;
  extraction_confidence?: number;
  confidence_score?: number;
  needs_review: boolean;
  needs_review_reason?: string;
  uploaded_at: string;
  created_at: string;
  verified_at?: string;
  extracted_data?: Record<string, any>;
  flags?: string[];
  transaction?: Transaction;
}

export interface ExtractedData {
  document_id: string;
  document_type: string;
  extracted_data: Record<string, any>;
  confidence?: number;
  confidence_score?: number;
  needs_review_items: string[];
  flags?: string[];
}

export interface Deadline {
  id: string;
  transaction_id: string;
  deadline_type: string;
  name: string;
  title: string;
  description?: string;
  due_date: string;
  status: string;
  days_remaining: number;
  notes?: string;
  completed_at?: string;
  source_document_id?: string;
  is_statutory: boolean;
  statutory_reference?: string;
  transaction?: Transaction;
}

export interface DeadlineSummary {
  id: string;
  name: string;
  due_date: string;
  status: string;
  days_remaining: number;
}

export interface UpcomingDeadline {
  id: string;
  name: string;
  title: string;
  due_date: string;
  days_remaining: number;
  status: string;
  deadline_type: string;
  transaction_id: string;
  property_address: PropertyAddress | string;
  is_statutory: boolean;
  transaction?: Transaction;
}

export interface DashboardData {
  active_transactions: number;
  pending_deadlines: number;
  documents_needing_review: number;
  completed_this_month: number;
  total_volume: number;
  pending_review?: number;
  closing_soon?: number;
  closed_this_month?: number;
  upcoming_closings?: {
    id: string;
    address: string;
    closing_date?: string;
  }[];
}

// Form Types

export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  organization_name: string;
  admin_email: string;
  admin_password: string;
  admin_name: string;
  license_number?: string;
  state?: string;
}

export interface CreateTransactionForm {
  transaction_type: 'purchase' | 'sale' | 'dual' | 'lease';
  property_address: PropertyAddress;
  purchase_price?: number;
  year_built?: number;
  notes?: string;
  closing_date?: string;
  buyer_name?: string;
  seller_name?: string;
}

export interface CreateDeadlineForm {
  transaction_id: string;
  name: string;
  due_date: string;
  deadline_type?: string;
  description?: string;
}

// Status helpers

export const TRANSACTION_STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  pending: 'Pending Review',
  active: 'Active',
  pending_close: 'Pending Close',
  closed: 'Closed',
  cancelled: 'Cancelled',
  on_hold: 'On Hold',
};

export const DOCUMENT_STATUS_LABELS: Record<string, string> = {
  uploaded: 'Processing',
  processing: 'Processing',
  extracted: 'Extracted',
  needs_review: 'Needs Review',
  verified: 'Verified',
  rejected: 'Rejected',
};

export const DEADLINE_STATUS_LABELS: Record<string, string> = {
  upcoming: 'Upcoming',
  due_soon: 'Due Soon',
  overdue: 'Overdue',
  completed: 'Completed',
  waived: 'Waived',
  extended: 'Extended',
};

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  purchase_contract: 'Purchase Contract',
  amendment: 'Amendment',
  addendum: 'Addendum',
  seller_disclosure: 'Seller Disclosure',
  lead_paint: 'Lead Paint Disclosure',
  hoa_disclosure: 'HOA Disclosure',
  inspection_report: 'Inspection Report',
  appraisal: 'Appraisal',
  title_commitment: 'Title Commitment',
  closing_disclosure: 'Closing Disclosure',
  pre_approval: 'Pre-Approval',
  other: 'Other',
};

// Report Types

export type DeadlineReportStatus = 'on_track' | 'due_soon' | 'overdue' | 'completed' | 'waived';
export type DocumentReportStatus = 'received' | 'pending' | 'needs_review' | 'verified' | 'missing';
export type RiskLevel = 'low' | 'medium' | 'high';

export interface PartyInfo {
  role: string;
  name: string;
  email?: string;
  phone?: string;
}

export interface DeadlineInfo {
  id: string;
  name: string;
  due_date: string;
  status: DeadlineReportStatus;
  days_remaining: number;
  is_statutory: boolean;
  completed_at?: string;
  notes?: string;
}

export interface DocumentInfo {
  id: string;
  document_type: string;
  filename: string;
  status: DocumentReportStatus;
  uploaded_at: string;
  verified_at?: string;
  extraction_confidence?: number;
  needs_review_reason?: string;
}

export interface ComplianceMetrics {
  total_deadlines: number;
  completed_deadlines: number;
  overdue_deadlines: number;
  upcoming_deadlines: number;
  deadline_compliance_rate: number;
  total_documents: number;
  verified_documents: number;
  pending_documents: number;
  needs_review_documents: number;
  document_completion_rate: number;
  overall_compliance_score: number;
  risk_level: RiskLevel;
}

export interface TransactionSummaryReport {
  report_id: string;
  report_type: string;
  generated_at: string;
  generated_by?: string;
  transaction_id: string;
  property_address: PropertyAddress;
  transaction_type: string;
  status: string;
  purchase_price?: number;
  effective_date?: string;
  closing_date?: string;
  days_to_closing?: number;
  parties: PartyInfo[];
  metrics: ComplianceMetrics;
  deadlines: DeadlineInfo[];
  documents: DocumentInfo[];
  warnings: string[];
  notes?: string;
}

export interface OrganizationOverviewReport {
  report_id: string;
  report_type: string;
  generated_at: string;
  organization_id: string;
  organization_name: string;
  total_transactions: number;
  active_transactions: number;
  pending_close_transactions: number;
  closed_this_month: number;
  overall_compliance_rate: number;
  transactions_at_risk: number;
  upcoming_closings: {
    id: string;
    address: string;
    closing_date?: string;
    days_remaining?: number;
  }[];
  overdue_deadlines: {
    id: string;
    name: string;
    due_date: string;
    transaction_id: string;
  }[];
  documents_needing_review: number;
}

export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  low: 'text-green-600 bg-green-100',
  medium: 'text-yellow-600 bg-yellow-100',
  high: 'text-red-600 bg-red-100',
};

export const DEADLINE_REPORT_STATUS_COLORS: Record<DeadlineReportStatus, string> = {
  on_track: 'text-green-600 bg-green-100',
  due_soon: 'text-yellow-600 bg-yellow-100',
  overdue: 'text-red-600 bg-red-100',
  completed: 'text-blue-600 bg-blue-100',
  waived: 'text-gray-600 bg-gray-100',
};
