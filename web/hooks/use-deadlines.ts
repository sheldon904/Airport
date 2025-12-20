import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Deadline, CreateDeadlineForm, UpcomingDeadline } from '@/types';

export function useDeadlines(transactionId?: string, params?: { status?: string; upcoming_days?: number }) {
  return useQuery<Deadline[]>({
    queryKey: ['deadlines', transactionId, params],
    queryFn: async () => {
      if (params?.upcoming_days) {
        return api.getUpcomingDeadlines(params.upcoming_days);
      }
      if (transactionId) {
        return api.listDeadlines(transactionId, params?.status !== 'pending');
      }
      return api.getUpcomingDeadlines(30);
    },
  });
}

export function useDeadline(id: string) {
  return useQuery<Deadline>({
    queryKey: ['deadlines', 'detail', id],
    queryFn: async () => {
      // API doesn't have single deadline endpoint
      throw new Error('Single deadline fetch not implemented');
    },
    enabled: false,
  });
}

export function useUpcomingDeadlines(days: number = 7) {
  return useQuery<UpcomingDeadline[]>({
    queryKey: ['deadlines', 'upcoming', days],
    queryFn: () => api.getUpcomingDeadlines(days),
  });
}

export function useCreateDeadline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateDeadlineForm) => api.createDeadline(data),
    onSuccess: (_, { transaction_id }) => {
      queryClient.invalidateQueries({ queryKey: ['deadlines', transaction_id] });
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['transactions', transaction_id] });
    },
  });
}

export function useUpdateDeadline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { due_date?: string; name?: string; notes?: string } }) =>
      api.updateDeadline(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['deadlines', 'detail', id] });
    },
  });
}

export function useCompleteDeadline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.completeDeadline(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['deadlines', 'detail', id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useWaiveDeadline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.waiveDeadline(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['deadlines', 'detail', id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useExtendDeadline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, newDate, reason }: { id: string; newDate: string; reason: string }) =>
      api.extendDeadline(id, newDate, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['deadlines', 'detail', id] });
    },
  });
}

export function useDeleteDeadline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteDeadline(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deadlines'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
}
