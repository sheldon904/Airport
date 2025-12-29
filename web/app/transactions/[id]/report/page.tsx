'use client';

import { useParams, useRouter } from 'next/navigation';
import { useTransactionReport, useDownloadReport } from '@/hooks/use-reports';
import {
  ArrowLeft,
  Download,
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  Users,
  Calendar,
  DollarSign,
  Home,
  Printer,
} from 'lucide-react';
import Link from 'next/link';
import {
  RISK_LEVEL_COLORS,
  DEADLINE_REPORT_STATUS_COLORS,
  DOCUMENT_TYPE_LABELS,
} from '@/types';

export default function TransactionReportPage() {
  const params = useParams();
  const router = useRouter();
  const transactionId = params.id as string;

  const { data: report, isLoading, error } = useTransactionReport(transactionId);
  const downloadMutation = useDownloadReport();

  if (isLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-40 bg-gray-200 rounded"></div>
          <div className="h-60 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="bg-red-50 text-red-700 p-4 rounded">
          Failed to load report. Please try again.
        </div>
      </div>
    );
  }

  const formatAddress = (addr: typeof report.property_address) => {
    let str = addr.street;
    if (addr.unit) str += ` ${addr.unit}`;
    return `${str}, ${addr.city}, ${addr.state} ${addr.zip_code}`;
  };

  const formatCurrency = (amount?: number) => {
    if (!amount) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'TBD';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Transaction Report
            </h1>
            <p className="text-gray-600">{formatAddress(report.property_address)}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => window.print()}
              className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
            >
              <Printer className="h-4 w-4" />
              Print
            </button>
            <button
              onClick={() => downloadMutation.mutate(transactionId)}
              disabled={downloadMutation.isPending}
              className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              {downloadMutation.isPending ? 'Downloading...' : 'Download'}
            </button>
          </div>
        </div>
      </div>

      {/* Risk Badge & Warnings */}
      <div className="flex items-center gap-4 mb-6">
        <span
          className={`px-3 py-1 rounded-full text-sm font-semibold uppercase ${
            RISK_LEVEL_COLORS[report.metrics.risk_level]
          }`}
        >
          {report.metrics.risk_level} Risk
        </span>
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700">
          {report.status.replace('_', ' ').toUpperCase()}
        </span>
      </div>

      {report.warnings.length > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 mb-6 rounded-r">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <h3 className="font-medium text-yellow-800">Attention Required</h3>
          </div>
          <ul className="mt-2 space-y-1">
            {report.warnings.map((warning, i) => (
              <li key={i} className="text-yellow-700 text-sm">
                • {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div
            className={`text-3xl font-bold ${
              report.metrics.overall_compliance_score >= 80
                ? 'text-green-600'
                : report.metrics.overall_compliance_score >= 50
                ? 'text-yellow-600'
                : 'text-red-600'
            }`}
          >
            {report.metrics.overall_compliance_score.toFixed(0)}%
          </div>
          <div className="text-xs text-gray-500 uppercase mt-1">
            Compliance Score
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-3xl font-bold text-gray-900">
            {report.metrics.completed_deadlines}/{report.metrics.total_deadlines}
          </div>
          <div className="text-xs text-gray-500 uppercase mt-1">
            Deadlines Complete
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-3xl font-bold text-gray-900">
            {report.metrics.verified_documents}/{report.metrics.total_documents}
          </div>
          <div className="text-xs text-gray-500 uppercase mt-1">
            Documents Verified
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-3xl font-bold text-gray-900">
            {report.days_to_closing ?? 'N/A'}
          </div>
          <div className="text-xs text-gray-500 uppercase mt-1">Days to Close</div>
        </div>
      </div>

      {/* Transaction Details */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Home className="h-5 w-5 text-gray-500" />
            Transaction Details
          </h2>
        </div>
        <div className="p-4 grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Purchase Price</p>
            <p className="text-xl font-semibold">
              {formatCurrency(report.purchase_price)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Closing Date</p>
            <p className="text-xl font-semibold">
              {formatDate(report.closing_date)}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Effective Date</p>
            <p className="font-medium">{formatDate(report.effective_date)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Transaction Type</p>
            <p className="font-medium capitalize">{report.transaction_type}</p>
          </div>
        </div>
      </div>

      {/* Parties */}
      {report.parties.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Users className="h-5 w-5 text-gray-500" />
              Parties
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Role
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Phone
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {report.parties.map((party, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3 text-sm capitalize">
                      {party.role.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">
                      {party.name}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {party.email || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {party.phone || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Deadline Timeline */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Calendar className="h-5 w-5 text-gray-500" />
            Deadline Timeline
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Deadline
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Due Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Days
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {report.deadlines.map((deadline) => (
                <tr key={deadline.id}>
                  <td className="px-4 py-3 text-sm">
                    {deadline.name}
                    {deadline.is_statutory && (
                      <span className="ml-1 text-xs text-gray-400">*</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {formatDate(deadline.due_date)}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {deadline.days_remaining >= 0
                      ? `${deadline.days_remaining}d`
                      : `${Math.abs(deadline.days_remaining)}d ago`}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        DEADLINE_REPORT_STATUS_COLORS[deadline.status]
                      }`}
                    >
                      {deadline.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-3 text-xs text-gray-500 border-t">
          * Statutory deadline
        </div>
      </div>

      {/* Document Checklist */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-gray-500" />
            Document Checklist
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Document Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Filename
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Uploaded
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {report.documents.map((doc) => (
                <tr key={doc.id}>
                  <td className="px-4 py-3 text-sm">
                    {DOCUMENT_TYPE_LABELS[doc.document_type] ||
                      doc.document_type.replace('_', ' ')}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 truncate max-w-xs">
                    {doc.filename}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        doc.status === 'verified'
                          ? 'bg-green-100 text-green-700'
                          : doc.status === 'needs_review'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {doc.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatDate(doc.uploaded_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-gray-400 py-4 border-t">
        <p>Report ID: {report.report_id}</p>
        <p>
          Generated {new Date(report.generated_at).toLocaleString()}
          {report.generated_by && ` by ${report.generated_by}`}
        </p>
        <p className="mt-2">
          This report is for informational purposes only and does not constitute
          legal advice.
        </p>
      </div>
    </div>
  );
}
