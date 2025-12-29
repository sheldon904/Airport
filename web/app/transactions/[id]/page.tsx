'use client';

import { useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useTransaction, useDeleteTransaction, useAddParty, useRemoveParty } from '@/hooks';
import { useDocuments, useUploadDocument } from '@/hooks';
import { useDeadlines, useCompleteDeadline } from '@/hooks';
import {
  ArrowLeft,
  Home,
  Calendar,
  DollarSign,
  FileText,
  Clock,
  Upload,
  CheckCircle,
  AlertCircle,
  Trash2,
  MoreVertical,
  Download,
  Eye,
  Loader2,
  Users,
  Plus,
  ChevronDown,
  ChevronUp,
  X,
  Phone,
  Mail,
  Building2,
  UserCircle,
} from 'lucide-react';
import Link from 'next/link';
import { formatCurrency, formatDate, getStatusColor, formatAddress } from '@/lib/utils';
import { useDropzone } from 'react-dropzone';
import type { Party } from '@/types';

const documentTypes = [
  { value: 'contract', label: 'Purchase Contract' },
  { value: 'addendum', label: 'Addendum' },
  { value: 'disclosure', label: 'Disclosure' },
  { value: 'inspection', label: 'Inspection Report' },
  { value: 'appraisal', label: 'Appraisal' },
  { value: 'title', label: 'Title Document' },
  { value: 'closing', label: 'Closing Document' },
  { value: 'other', label: 'Other' },
];

const partyRoles = [
  { value: 'buyer', label: 'Buyer' },
  { value: 'seller', label: 'Seller' },
  { value: 'buyer_agent', label: 'Buyer Agent' },
  { value: 'seller_agent', label: 'Seller/Listing Agent' },
  { value: 'title_company', label: 'Title Company' },
  { value: 'lender', label: 'Lender' },
  { value: 'appraiser', label: 'Appraiser' },
  { value: 'inspector', label: 'Inspector' },
  { value: 'attorney', label: 'Attorney' },
  { value: 'escrow', label: 'Escrow Officer' },
  { value: 'other', label: 'Other' },
];

function PartyCard({
  party,
  onRemove,
  isRemoving,
}: {
  party: Party;
  onRemove: () => void;
  isRemoving: boolean;
}) {
  const roleLabel = partyRoles.find((r) => r.value === party.role)?.label || party.role;

  return (
    <div className="border rounded-lg p-4 hover:border-primary-300 transition-colors bg-white">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <UserCircle className="h-10 w-10 text-gray-400" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900">{party.name}</p>
            <p className="text-xs text-primary-600 font-medium">{roleLabel}</p>
            <div className="mt-2 space-y-1">
              {party.email && (
                <div className="flex items-center text-xs text-gray-500">
                  <Mail className="h-3 w-3 mr-1.5" />
                  <a href={`mailto:${party.email}`} className="hover:text-primary-600">
                    {party.email}
                  </a>
                </div>
              )}
              {party.phone && (
                <div className="flex items-center text-xs text-gray-500">
                  <Phone className="h-3 w-3 mr-1.5" />
                  <a href={`tel:${party.phone}`} className="hover:text-primary-600">
                    {party.phone}
                  </a>
                </div>
              )}
              {party.company && (
                <div className="flex items-center text-xs text-gray-500">
                  <Building2 className="h-3 w-3 mr-1.5" />
                  {party.company}
                </div>
              )}
              {party.license_number && (
                <div className="text-xs text-gray-400">
                  License: {party.license_number}
                </div>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={onRemove}
          disabled={isRemoving}
          className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-50"
          title="Remove party"
        >
          {isRemoving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}

function AddPartyForm({
  onAdd,
  onCancel,
  isAdding,
}: {
  onAdd: (party: Omit<Party, 'id'>) => void;
  onCancel: () => void;
  isAdding: boolean;
}) {
  const [formData, setFormData] = useState({
    role: 'buyer',
    name: '',
    email: '',
    phone: '',
    company: '',
    license_number: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    onAdd({
      role: formData.role,
      name: formData.name.trim(),
      email: formData.email.trim() || undefined,
      phone: formData.phone.trim() || undefined,
      company: formData.company.trim() || undefined,
      license_number: formData.license_number.trim() || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="border rounded-lg p-4 bg-gray-50 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-900">Add New Party</h4>
        <button
          type="button"
          onClick={onCancel}
          className="p-1 text-gray-400 hover:text-gray-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2 sm:col-span-1">
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Role *
          </label>
          <select
            value={formData.role}
            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            className="w-full text-sm rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          >
            {partyRoles.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </div>

        <div className="col-span-2 sm:col-span-1">
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full text-sm rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            placeholder="John Smith"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full text-sm rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            placeholder="john@example.com"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Phone
          </label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full text-sm rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            placeholder="(555) 123-4567"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Company
          </label>
          <input
            type="text"
            value={formData.company}
            onChange={(e) => setFormData({ ...formData, company: e.target.value })}
            className="w-full text-sm rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            placeholder="ABC Realty"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            License #
          </label>
          <input
            type="text"
            value={formData.license_number}
            onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
            className="w-full text-sm rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            placeholder="BK1234567"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isAdding || !formData.name.trim()}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          {isAdding ? (
            <>
              <Loader2 className="h-3 w-3 mr-1.5 animate-spin" />
              Adding...
            </>
          ) : (
            <>
              <Plus className="h-3 w-3 mr-1.5" />
              Add Party
            </>
          )}
        </button>
      </div>
    </form>
  );
}

function DocumentCard({
  id,
  filename,
  documentType,
  status,
  extractionStatus,
  confidenceScore,
  createdAt,
  transactionId,
}: {
  id: string;
  filename: string;
  documentType: string;
  status: string;
  extractionStatus: string;
  confidenceScore?: number;
  createdAt: string;
  transactionId: string;
}) {
  const typeLabel = documentTypes.find((t) => t.value === documentType)?.label || documentType;

  const getExtractionBadge = () => {
    if (extractionStatus === 'completed') {
      if (confidenceScore && confidenceScore >= 0.85) {
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
            <CheckCircle className="h-3 w-3 mr-1" />
            Verified
          </span>
        );
      }
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
          <AlertCircle className="h-3 w-3 mr-1" />
          Needs Review
        </span>
      );
    }
    if (extractionStatus === 'processing') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          Processing
        </span>
      );
    }
    if (extractionStatus === 'failed') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
          Failed
        </span>
      );
    }
    return null;
  };

  return (
    <div className="border rounded-lg p-4 hover:border-primary-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <FileText className="h-8 w-8 text-gray-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 truncate max-w-xs">
              {filename}
            </p>
            <p className="text-xs text-gray-500">{typeLabel}</p>
            <p className="text-xs text-gray-400 mt-1">{formatDate(createdAt)}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {getExtractionBadge()}
          <Link
            href={`/documents/${id}`}
            className="p-1 text-gray-400 hover:text-gray-600"
          >
            <Eye className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

function DeadlineCard({
  id,
  title,
  dueDate,
  status,
  isStatutory,
  onComplete,
  isCompleting,
}: {
  id: string;
  title: string;
  dueDate: string;
  status: string;
  isStatutory: boolean;
  onComplete: () => void;
  isCompleting: boolean;
}) {
  const isOverdue = new Date(dueDate) < new Date() && status === 'pending';
  const isPending = status === 'pending';

  return (
    <div
      className={`border rounded-lg p-4 ${
        isOverdue ? 'border-red-300 bg-red-50' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Clock
            className={`h-5 w-5 ${isOverdue ? 'text-red-500' : 'text-gray-400'}`}
          />
          <div>
            <p className="text-sm font-medium text-gray-900">{title}</p>
            <div className="flex items-center space-x-2 mt-1">
              <span
                className={`text-xs ${
                  isOverdue ? 'text-red-600 font-medium' : 'text-gray-500'
                }`}
              >
                {isOverdue ? 'Overdue: ' : 'Due: '}
                {formatDate(dueDate)}
              </span>
              {isStatutory && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                  Statutory
                </span>
              )}
            </div>
          </div>
        </div>
        {isPending && (
          <button
            onClick={onComplete}
            disabled={isCompleting}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded shadow-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
          >
            {isCompleting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <>
                <CheckCircle className="h-3 w-3 mr-1" />
                Complete
              </>
            )}
          </button>
        )}
        {status === 'completed' && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
            <CheckCircle className="h-3 w-3 mr-1" />
            Completed
          </span>
        )}
      </div>
    </div>
  );
}

export default function TransactionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const transactionId = params.id as string;

  const { data: transaction, isLoading: txLoading } = useTransaction(transactionId);
  const { data: documents, isLoading: docsLoading } = useDocuments(transactionId);
  const { data: deadlines, isLoading: deadlinesLoading } = useDeadlines(transactionId);
  const deleteTransaction = useDeleteTransaction();
  const uploadDocument = useUploadDocument();
  const completeDeadline = useCompleteDeadline();
  const addParty = useAddParty();
  const removeParty = useRemoveParty();

  const [selectedDocType, setSelectedDocType] = useState('contract');
  const [completingDeadlineId, setCompletingDeadlineId] = useState<string | null>(null);
  const [showParties, setShowParties] = useState(true);
  const [showAddParty, setShowAddParty] = useState(false);
  const [removingPartyId, setRemovingPartyId] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        await uploadDocument.mutateAsync({
          transactionId,
          file,
          documentType: selectedDocType,
        });
      }
    },
    [transactionId, selectedDocType, uploadDocument]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
  });

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this transaction?')) {
      await deleteTransaction.mutateAsync(transactionId);
      router.push('/transactions');
    }
  };

  const handleCompleteDeadline = async (deadlineId: string) => {
    setCompletingDeadlineId(deadlineId);
    try {
      await completeDeadline.mutateAsync(deadlineId);
    } finally {
      setCompletingDeadlineId(null);
    }
  };

  const handleAddParty = async (party: Omit<Party, 'id'>) => {
    try {
      await addParty.mutateAsync({ transactionId, party });
      setShowAddParty(false);
    } catch (error) {
      console.error('Failed to add party:', error);
    }
  };

  const handleRemoveParty = async (partyId: string) => {
    if (!confirm('Are you sure you want to remove this party?')) return;
    setRemovingPartyId(partyId);
    try {
      await removeParty.mutateAsync({ transactionId, partyId });
    } catch (error) {
      console.error('Failed to remove party:', error);
    } finally {
      setRemovingPartyId(null);
    }
  };

  if (txLoading) {
    return (
      <DashboardLayout>
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-64 bg-gray-200 rounded-lg" />
        </div>
      </DashboardLayout>
    );
  }

  if (!transaction) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <h2 className="text-xl font-medium text-gray-900">Transaction not found</h2>
          <Link
            href="/transactions"
            className="mt-4 inline-flex items-center text-primary-600 hover:text-primary-500"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to transactions
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  const statusColors = getStatusColor(transaction.status);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <Link
              href="/transactions"
              className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to transactions
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">
              {formatAddress(transaction.property_address)}
            </h1>
            <div className="flex items-center space-x-4 mt-2">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors}`}
              >
                {transaction.status.replace('_', ' ')}
              </span>
              <span className="text-sm text-gray-500 capitalize">
                {transaction.transaction_type}
              </span>
            </div>
          </div>
          <button
            onClick={handleDelete}
            className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </button>
        </div>

        {/* Transaction Details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Info Card */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                Transaction Details
              </h2>
              <dl className="grid grid-cols-2 gap-4">
                {transaction.purchase_price && (
                  <div>
                    <dt className="text-sm text-gray-500 flex items-center">
                      <DollarSign className="h-4 w-4 mr-1" />
                      Purchase Price
                    </dt>
                    <dd className="mt-1 text-lg font-medium text-gray-900">
                      {formatCurrency(transaction.purchase_price)}
                    </dd>
                  </div>
                )}
                {transaction.closing_date && (
                  <div>
                    <dt className="text-sm text-gray-500 flex items-center">
                      <Calendar className="h-4 w-4 mr-1" />
                      Closing Date
                    </dt>
                    <dd className="mt-1 text-lg font-medium text-gray-900">
                      {formatDate(transaction.closing_date)}
                    </dd>
                  </div>
                )}
                {transaction.buyer_name && (
                  <div>
                    <dt className="text-sm text-gray-500">Buyer</dt>
                    <dd className="mt-1 font-medium text-gray-900">
                      {transaction.buyer_name}
                    </dd>
                  </div>
                )}
                {transaction.seller_name && (
                  <div>
                    <dt className="text-sm text-gray-500">Seller</dt>
                    <dd className="mt-1 font-medium text-gray-900">
                      {transaction.seller_name}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Parties Section */}
            <div className="bg-white shadow rounded-lg">
              <button
                onClick={() => setShowParties(!showParties)}
                className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition-colors rounded-t-lg"
              >
                <div className="flex items-center">
                  <Users className="h-5 w-5 text-gray-400 mr-2" />
                  <h2 className="text-lg font-medium text-gray-900">
                    Parties ({transaction.parties?.length || 0})
                  </h2>
                </div>
                {showParties ? (
                  <ChevronUp className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                )}
              </button>

              {showParties && (
                <div className="px-6 pb-6 space-y-4">
                  {/* Parties list */}
                  {transaction.parties && transaction.parties.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {transaction.parties.map((party) => (
                        <PartyCard
                          key={party.id}
                          party={party}
                          onRemove={() => party.id && handleRemoveParty(party.id)}
                          isRemoving={removingPartyId === party.id}
                        />
                      ))}
                    </div>
                  ) : (
                    !showAddParty && (
                      <p className="text-sm text-gray-500 text-center py-4">
                        No parties added yet
                      </p>
                    )
                  )}

                  {/* Add party form or button */}
                  {showAddParty ? (
                    <AddPartyForm
                      onAdd={handleAddParty}
                      onCancel={() => setShowAddParty(false)}
                      isAdding={addParty.isPending}
                    />
                  ) : (
                    <button
                      onClick={() => setShowAddParty(true)}
                      className="inline-flex items-center px-3 py-2 text-sm font-medium text-primary-600 bg-primary-50 rounded-md hover:bg-primary-100 transition-colors"
                    >
                      <Plus className="h-4 w-4 mr-1.5" />
                      Add Party
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Documents */}
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium text-gray-900">Documents</h2>
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="text-sm rounded-md border-gray-300"
                >
                  {documentTypes.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Upload Zone */}
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="mx-auto h-8 w-8 text-gray-400" />
                <p className="mt-2 text-sm text-gray-600">
                  {isDragActive
                    ? 'Drop the files here...'
                    : 'Drag & drop files here, or click to select'}
                </p>
                <p className="mt-1 text-xs text-gray-500">PDF, PNG, JPG up to 10MB</p>
                {uploadDocument.isPending && (
                  <div className="mt-2 flex items-center justify-center text-primary-600">
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Uploading...
                  </div>
                )}
              </div>

              {/* Document List */}
              <div className="mt-4 space-y-3">
                {docsLoading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2].map((i) => (
                      <div key={i} className="h-20 bg-gray-100 rounded-lg" />
                    ))}
                  </div>
                ) : documents && documents.length > 0 ? (
                  documents.map((doc) => (
                    <DocumentCard
                      key={doc.id}
                      id={doc.id}
                      filename={doc.filename}
                      documentType={doc.document_type}
                      status={doc.status}
                      extractionStatus={doc.extraction_status}
                      confidenceScore={doc.confidence_score}
                      createdAt={doc.created_at}
                      transactionId={transactionId}
                    />
                  ))
                ) : (
                  <p className="text-center text-sm text-gray-500 py-4">
                    No documents uploaded yet
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar - Deadlines */}
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Deadlines</h2>
              <div className="space-y-3">
                {deadlinesLoading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-16 bg-gray-100 rounded-lg" />
                    ))}
                  </div>
                ) : deadlines && deadlines.length > 0 ? (
                  deadlines.map((deadline) => (
                    <DeadlineCard
                      key={deadline.id}
                      id={deadline.id}
                      title={deadline.title}
                      dueDate={deadline.due_date}
                      status={deadline.status}
                      isStatutory={deadline.is_statutory}
                      onComplete={() => handleCompleteDeadline(deadline.id)}
                      isCompleting={completingDeadlineId === deadline.id}
                    />
                  ))
                ) : (
                  <p className="text-center text-sm text-gray-500 py-4">
                    No deadlines set
                  </p>
                )}
              </div>
              <Link
                href={`/deadlines?transaction=${transactionId}`}
                className="mt-4 block text-center text-sm font-medium text-primary-600 hover:text-primary-500"
              >
                Manage deadlines
              </Link>
            </div>

            {/* Checklist Progress */}
            {transaction.checklist && (
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">
                  Checklist Progress
                </h2>
                <div className="space-y-2">
                  {Object.entries(transaction.checklist).map(([key, value]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between py-1"
                    >
                      <span className="text-sm text-gray-600 capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      {value ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
