import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { DEMO_MODE, mockTransactions, mockDashboard } from '@/lib/mock-data';
import { Transaction, DashboardData, CreateTransactionForm, Party } from '@/types';

export function useTransactions(params?: { status?: string; limit?: number; offset?: number }) {
  return useQuery<Transaction[]>({
    queryKey: ['transactions', params],
    queryFn: async () => {
      if (DEMO_MODE) {
        const limit = params?.limit || 20;
        return mockTransactions.slice(0, limit);
      }
      const result = await api.listTransactions(1, params?.limit || 20, params?.status);
      return result.items || result;
    },
  });
}

export function useTransaction(id: string) {
  return useQuery({
    queryKey: ['transactions', id],
    queryFn: () => {
      if (DEMO_MODE) {
        const tx = mockTransactions.find(t => t.id === id);
        return tx || mockTransactions[0];
      }
      return api.getTransaction(id);
    },
    enabled: !!id,
  });
}

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => {
      if (DEMO_MODE) {
        return Promise.resolve(mockDashboard);
      }
      return api.getDashboard();
    },
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateTransactionForm) => api.createTransaction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateTransactionForm> }) =>
      api.updateTransaction(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['transactions', id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteTransaction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useAddParty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      transactionId,
      party,
    }: {
      transactionId: string;
      party: Omit<Party, 'id'>;
    }) => api.addParty(transactionId, party),
    onSuccess: (_, { transactionId }) => {
      queryClient.invalidateQueries({ queryKey: ['transactions', transactionId] });
    },
  });
}

export function useRemoveParty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      transactionId,
      partyId,
    }: {
      transactionId: string;
      partyId: string;
    }) => api.removeParty(transactionId, partyId),
    onSuccess: (_, { transactionId }) => {
      queryClient.invalidateQueries({ queryKey: ['transactions', transactionId] });
    },
  });
}
