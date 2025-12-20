import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Document, ExtractedData } from '@/types';

export function useDocuments(transactionId?: string, params?: { status?: string }) {
  return useQuery<Document[]>({
    queryKey: ['documents', transactionId, params],
    queryFn: async () => {
      if (params?.status === 'needs_review') {
        return api.getReviewQueue();
      }
      if (transactionId) {
        return api.listDocuments(transactionId, undefined, params?.status);
      }
      return [];
    },
  });
}

export function useDocument(id: string) {
  return useQuery<Document>({
    queryKey: ['documents', 'detail', id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
  });
}

export function useDocumentExtraction(id: string) {
  return useQuery<ExtractedData>({
    queryKey: ['documents', 'extraction', id],
    queryFn: () => api.getExtractedData(id),
    enabled: !!id,
  });
}

export function useDocumentsNeedingReview() {
  return useQuery<Document[]>({
    queryKey: ['documents', 'review'],
    queryFn: () => api.getReviewQueue(),
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      transactionId,
      file,
      documentType,
    }: {
      transactionId: string;
      file: File;
      documentType: string;
    }) => api.uploadDocument(transactionId, file, documentType),
    onSuccess: (_, { transactionId }) => {
      queryClient.invalidateQueries({ queryKey: ['documents', transactionId] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['transactions', transactionId] });
    },
  });
}

export function useVerifyDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      verified,
      corrections,
    }: {
      id: string;
      verified: boolean;
      corrections?: Record<string, any>;
    }) => {
      if (verified) {
        return api.verifyDocument(id, corrections);
      }
      return api.reprocessDocument(id);
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['documents', 'detail', id] });
      queryClient.invalidateQueries({ queryKey: ['documents', 'extraction', id] });
      queryClient.invalidateQueries({ queryKey: ['documents', 'review'] });
    },
  });
}

export function useReprocessDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.reprocessDocument(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['documents', 'detail', id] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
}
