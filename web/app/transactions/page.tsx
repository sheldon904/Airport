'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useTransactions, useCreateTransaction } from '@/hooks';
import {
  Plus,
  Search,
  Filter,
  ChevronRight,
  Home,
  Calendar,
  DollarSign,
  Loader2,
  X,
} from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { formatCurrency, formatDate, getStatusColor, formatAddress } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const transactionSchema = z.object({
  property_address: z.object({
    street: z.string().min(1, 'Street address is required'),
    city: z.string().min(1, 'City is required'),
    state: z.string().min(1, 'State is required'),
    zip_code: z.string().min(5, 'Valid ZIP code is required'),
  }),
  transaction_type: z.enum(['purchase', 'sale', 'lease']),
  purchase_price: z.number().min(0).optional(),
  closing_date: z.string().optional(),
  buyer_name: z.string().optional(),
  seller_name: z.string().optional(),
});

type TransactionFormData = z.infer<typeof transactionSchema>;

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'under_contract', label: 'Under Contract' },
  { value: 'inspection', label: 'Inspection' },
  { value: 'appraisal', label: 'Appraisal' },
  { value: 'closing', label: 'Closing' },
  { value: 'closed', label: 'Closed' },
  { value: 'cancelled', label: 'Cancelled' },
];

function CreateTransactionModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const createTransaction = useCreateTransaction();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TransactionFormData>({
    resolver: zodResolver(transactionSchema),
    defaultValues: {
      transaction_type: 'purchase',
      property_address: {
        state: 'FL',
      },
    },
  });

  const onSubmit = async (data: TransactionFormData) => {
    try {
      await createTransaction.mutateAsync({
        ...data,
        purchase_price: data.purchase_price || undefined,
        closing_date: data.closing_date || undefined,
      });
      reset();
      onClose();
    } catch (err) {
      console.error('Failed to create transaction:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={onClose} />
        <div className="relative w-full max-w-lg rounded-lg bg-white shadow-xl">
          <div className="flex items-center justify-between border-b px-6 py-4">
            <h2 className="text-lg font-medium text-gray-900">
              New Transaction
            </h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="h-5 w-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Transaction Type
              </label>
              <select
                {...register('transaction_type')}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              >
                <option value="purchase">Purchase</option>
                <option value="sale">Sale</option>
                <option value="lease">Lease</option>
              </select>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-700">Property Address</h3>
              <input
                {...register('property_address.street')}
                placeholder="Street Address"
                className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              />
              {errors.property_address?.street && (
                <p className="text-sm text-red-600">
                  {errors.property_address.street.message}
                </p>
              )}
              <div className="grid grid-cols-3 gap-3">
                <input
                  {...register('property_address.city')}
                  placeholder="City"
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                />
                <input
                  {...register('property_address.state')}
                  placeholder="State"
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                />
                <input
                  {...register('property_address.zip_code')}
                  placeholder="ZIP Code"
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Purchase Price
                </label>
                <input
                  {...register('purchase_price', { valueAsNumber: true })}
                  type="number"
                  placeholder="0"
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Closing Date
                </label>
                <input
                  {...register('closing_date')}
                  type="date"
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Buyer Name
                </label>
                <input
                  {...register('buyer_name')}
                  placeholder="John Doe"
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Seller Name
                </label>
                <input
                  {...register('seller_name')}
                  placeholder="Jane Smith"
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createTransaction.isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {createTransaction.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Plus className="h-4 w-4 mr-2" />
                )}
                Create Transaction
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function TransactionsPage() {
  const searchParams = useSearchParams();
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(searchParams.get('new') === 'true');

  const { data: transactions, isLoading } = useTransactions({
    status: statusFilter || undefined,
  });

  const filteredTransactions = transactions?.filter((tx) => {
    if (!searchQuery) return true;
    const address = formatAddress(tx.property_address).toLowerCase();
    return (
      address.includes(searchQuery.toLowerCase()) ||
      tx.buyer_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.seller_name?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
            <p className="mt-1 text-sm text-gray-500">
              Manage your real estate transactions
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Transaction
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by address, buyer, or seller..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-4 py-2 rounded-md border border-gray-300 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            />
          </div>
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-gray-400 mr-2" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Transaction List */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : filteredTransactions && filteredTransactions.length > 0 ? (
          <div className="bg-white shadow rounded-lg divide-y divide-gray-200">
            {filteredTransactions.map((tx) => {
              const statusColors = getStatusColor(tx.status);
              return (
                <Link
                  key={tx.id}
                  href={`/transactions/${tx.id}`}
                  className="block hover:bg-gray-50 transition-colors"
                >
                  <div className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                          <div className="h-12 w-12 rounded-lg bg-primary-100 flex items-center justify-center">
                            <Home className="h-6 w-6 text-primary-600" />
                          </div>
                        </div>
                        <div>
                          <p className="text-lg font-medium text-gray-900">
                            {formatAddress(tx.property_address)}
                          </p>
                          <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
                            <span className="capitalize">{tx.transaction_type}</span>
                            {tx.buyer_name && <span>Buyer: {tx.buyer_name}</span>}
                            {tx.seller_name && <span>Seller: {tx.seller_name}</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-6">
                        {tx.purchase_price && (
                          <div className="text-right">
                            <div className="flex items-center text-gray-500">
                              <DollarSign className="h-4 w-4 mr-1" />
                              <span className="text-sm">Price</span>
                            </div>
                            <p className="font-medium text-gray-900">
                              {formatCurrency(tx.purchase_price)}
                            </p>
                          </div>
                        )}
                        {tx.closing_date && (
                          <div className="text-right">
                            <div className="flex items-center text-gray-500">
                              <Calendar className="h-4 w-4 mr-1" />
                              <span className="text-sm">Closing</span>
                            </div>
                            <p className="font-medium text-gray-900">
                              {formatDate(tx.closing_date)}
                            </p>
                          </div>
                        )}
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors}`}
                        >
                          {tx.status.replace('_', ' ')}
                        </span>
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <Home className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No transactions</h3>
            <p className="mt-2 text-sm text-gray-500">
              Get started by creating your first transaction.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Transaction
            </button>
          </div>
        )}
      </div>

      <CreateTransactionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </DashboardLayout>
  );
}
