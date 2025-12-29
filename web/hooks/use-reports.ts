import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { TransactionSummaryReport, OrganizationOverviewReport, DashboardData } from '@/types';

export function useTransactionReport(transactionId: string, enabled = true) {
  return useQuery<TransactionSummaryReport>({
    queryKey: ['reports', 'transaction', transactionId],
    queryFn: () => api.getTransactionReport(transactionId),
    enabled: !!transactionId && enabled,
    staleTime: 5 * 60 * 1000, // Reports are fresh for 5 minutes
  });
}

export function useOrganizationReport() {
  return useQuery<OrganizationOverviewReport>({
    queryKey: ['reports', 'organization'],
    queryFn: () => api.getOrganizationReport(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useDashboardMetrics() {
  return useQuery<DashboardData>({
    queryKey: ['reports', 'dashboard'],
    queryFn: () => api.getDashboardMetrics(),
    staleTime: 60 * 1000, // Dashboard refreshes every minute
  });
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: async (transactionId: string) => {
      const blob = await api.downloadTransactionReport(transactionId);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `transaction-report-${transactionId}.html`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return true;
    },
  });
}
