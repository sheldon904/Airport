import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { DEMO_MODE, mockUpcomingDeadlines } from '@/lib/mock-data';
import { Deadline, CreateDeadlineForm, UpcomingDeadline } from '@/types';

export function useDeadlines(transactionId?: string, params?: { status?: string; upcoming_days?: number }) {
  return useQuery<Deadline[]>({
    queryKey: ['deadlines', transactionId, params],
    queryFn: async () => {
      if (DEMO_MODE) {
        return mockUpcomingDeadlines as unknown as Deadline[];
      }
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
    queryFn: () => {
      if (DEMO_MODE) {
        const dl = mockUpcomingDeadlines.find(d => d.id === id);
        return (dl || mockUpcomingDeadlines[0]) as unknown as Deadline;
      }
      return api.getDeadline(id);
    },
    enabled: !!id,
  });
}

export function useUpcomingDeadlines(days: number = 7) {
  return useQuery<UpcomingDeadline[]>({
    queryKey: ['deadlines', 'upcoming', days],
    queryFn: () => {
      if (DEMO_MODE) {
        return Promise.resolve(mockUpcomingDeadlines);
      }
      return api.getUpcomingDeadlines(days);
    },
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
