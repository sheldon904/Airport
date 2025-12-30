import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, parseISO, differenceInDays, isPast, startOfDay } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return format(d, 'MMM d, yyyy');
}

export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return format(d, 'MMM d, yyyy h:mm a');
}

export function formatRelativeDate(date: string | Date): string {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return formatDistanceToNow(d, { addSuffix: true });
}

export function getDaysUntil(date: string | Date): number {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return differenceInDays(d, new Date());
}

/**
 * Check if a date is overdue (past end of day).
 * Properly handles date-only values without timezone issues.
 */
export function isOverdue(date: string | Date): boolean {
  const d = typeof date === 'string' ? parseISO(date) : date;
  // Compare start of days to avoid timezone issues with date-only values
  const today = startOfDay(new Date());
  const dueDate = startOfDay(d);
  return isPast(dueDate) && dueDate < today;
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatAddress(address: {
  street?: string;
  unit?: string;
  city?: string;
  state?: string;
  zip_code?: string;
} | string | null | undefined): string {
  if (!address) return 'Address not available';
  if (typeof address === 'string') return address;

  const parts: string[] = [];
  if (address.street) parts.push(address.street);
  if (address.unit) parts.push(`Unit ${address.unit}`);
  if (address.city && address.state && address.zip_code) {
    parts.push(`${address.city}, ${address.state} ${address.zip_code}`);
  } else if (address.city) {
    parts.push(address.city);
  }
  return parts.length > 0 ? parts.join(', ') : 'Address not available';
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    // Transaction statuses
    draft: 'gray',
    pending: 'yellow',
    active: 'blue',
    pending_close: 'purple',
    closed: 'green',
    cancelled: 'red',
    on_hold: 'orange',
    // Document statuses
    uploaded: 'gray',
    processing: 'yellow',
    extracted: 'blue',
    needs_review: 'orange',
    verified: 'green',
    rejected: 'red',
    // Deadline statuses
    upcoming: 'blue',
    due_soon: 'yellow',
    overdue: 'red',
    completed: 'green',
    waived: 'gray',
    extended: 'purple',
  };
  return colors[status] || 'gray';
}

export function getBadgeClass(status: string): string {
  const color = getStatusColor(status);
  const classes: Record<string, string> = {
    gray: 'badge-gray',
    yellow: 'badge-warning',
    blue: 'badge-info',
    green: 'badge-success',
    red: 'badge-danger',
    orange: 'bg-orange-100 text-orange-800',
    purple: 'bg-purple-100 text-purple-800',
  };
  return classes[color] || 'badge-gray';
}
