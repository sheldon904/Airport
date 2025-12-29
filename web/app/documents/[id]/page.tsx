'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { api } from '@/lib/api';
import {
  ArrowLeft,
  FileText,
  Download,
  ExternalLink,
  CheckCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
  Edit2,
  Save,
  X,
} from 'lucide-react';
import { formatDate, formatCurrency } from '@/lib/utils';
import type { Document, ExtractedData } from '@/types';

interface DocumentViewerProps {
  document: Document;
  extractedData: ExtractedData | null;
  onVerify: () => void;
  onReprocess: () => void;
  isVerifying: boolean;
  isReprocessing: boolean;
}

function ExtractionDataView({
  data,
  isEditing,
  onEdit,
  editedData,
  setEditedData,
}: {
  data: ExtractedData;
  isEditing: boolean;
  onEdit: (field: string, value: any) => void;
  editedData: Record<string, any>;
  setEditedData: (data: Record<string, any>) => void;
}) {
  return (
    <div className="space-y-6">
      {/* Property Address */}
      {data.property_address && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Property Address</h4>
          <div className="bg-gray-50 rounded-lg p-3 text-sm">
            <p>{data.property_address.street}</p>
            {data.property_address.unit && <p>Unit {data.property_address.unit}</p>}
            <p>
              {data.property_address.city}, {data.property_address.state}{' '}
              {data.property_address.zip_code}
            </p>
            {data.property_address.county && (
              <p className="text-gray-500">{data.property_address.county} County</p>
            )}
          </div>
        </div>
      )}

      {/* Financial Terms */}
      <div>
        <h4 className="text-sm font-medium text-gray-900 mb-2">Financial Terms</h4>
        <dl className="grid grid-cols-2 gap-3">
          {data.purchase_price && (
            <div className="bg-gray-50 rounded-lg p-3">
              <dt className="text-xs text-gray-500">Purchase Price</dt>
              <dd className="text-sm font-medium">{formatCurrency(data.purchase_price)}</dd>
            </div>
          )}
          {data.earnest_money && (
            <div className="bg-gray-50 rounded-lg p-3">
              <dt className="text-xs text-gray-500">Earnest Money</dt>
              <dd className="text-sm font-medium">{formatCurrency(data.earnest_money)}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Key Dates */}
      {(data.effective_date || data.closing_date) && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Key Dates</h4>
          <dl className="grid grid-cols-2 gap-3">
            {data.effective_date && (
              <div className="bg-gray-50 rounded-lg p-3">
                <dt className="text-xs text-gray-500">Effective Date</dt>
                <dd className="text-sm font-medium">{formatDate(data.effective_date)}</dd>
              </div>
            )}
            {data.closing_date && (
              <div className="bg-gray-50 rounded-lg p-3">
                <dt className="text-xs text-gray-500">Closing Date</dt>
                <dd className="text-sm font-medium">{formatDate(data.closing_date)}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {/* Parties */}
      {data.parties && data.parties.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Parties</h4>
          <div className="space-y-2">
            {data.parties.map((party, idx) => (
              <div key={idx} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500 uppercase">
                    {party.role.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-sm font-medium mt-1">{party.name}</p>
                {party.email && <p className="text-xs text-gray-500">{party.email}</p>}
                {party.phone && <p className="text-xs text-gray-500">{party.phone}</p>}
                {party.company && <p className="text-xs text-gray-500">{party.company}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contingencies */}
      {data.contingencies && data.contingencies.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Contingencies</h4>
          <div className="space-y-2">
            {data.contingencies.map((contingency, idx) => (
              <div key={idx} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">
                    {contingency.contingency_type.replace('_', ' ')}
                  </span>
                  {contingency.waived && (
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                      Waived
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-600 mt-1">{contingency.description}</p>
                {contingency.deadline_date && (
                  <p className="text-xs text-gray-500 mt-1">
                    Deadline: {formatDate(contingency.deadline_date)}
                  </p>
                )}
                {contingency.days_from_effective && !contingency.deadline_date && (
                  <p className="text-xs text-gray-500 mt-1">
                    {contingency.days_from_effective} days from effective date
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unclear Items */}
      {data.unclear_items && data.unclear_items.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-yellow-700 mb-2 flex items-center">
            <AlertCircle className="h-4 w-4 mr-1" />
            Items Requiring Review
          </h4>
          <ul className="bg-yellow-50 rounded-lg p-3 space-y-1">
            {data.unclear_items.map((item, idx) => (
              <li key={idx} className="text-sm text-yellow-700">
                • {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Missing Signatures */}
      {data.missing_signatures && data.missing_signatures.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-red-700 mb-2 flex items-center">
            <AlertCircle className="h-4 w-4 mr-1" />
            Missing Signatures
          </h4>
          <ul className="bg-red-50 rounded-lg p-3 space-y-1">
            {data.missing_signatures.map((sig, idx) => (
              <li key={idx} className="text-sm text-red-700">
                • {sig}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function DocumentViewerPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const [document, setDocument] = useState<Document | null>(null);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDocument() {
      try {
        setIsLoading(true);
        setError(null);

        const [doc, urlData] = await Promise.all([
          api.getDocument(documentId),
          api.getDocumentDownloadUrl(documentId),
        ]);

        setDocument(doc);
        setDownloadUrl(urlData.url);

        // Load extracted data if available
        if (doc.status === 'extracted' || doc.status === 'needs_review' || doc.status === 'verified') {
          try {
            const extracted = await api.getExtractedData(documentId);
            setExtractedData(extracted);
          } catch {
            // Extraction data might not be available
          }
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load document');
      } finally {
        setIsLoading(false);
      }
    }

    loadDocument();
  }, [documentId]);

  const handleVerify = async () => {
    try {
      setIsVerifying(true);
      await api.verifyDocument(documentId);
      // Reload document to get updated status
      const doc = await api.getDocument(documentId);
      setDocument(doc);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to verify document');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleReprocess = async () => {
    try {
      setIsReprocessing(true);
      await api.reprocessDocument(documentId);
      // Reload document
      const doc = await api.getDocument(documentId);
      setDocument(doc);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reprocess document');
    } finally {
      setIsReprocessing(false);
    }
  };

  const handleDownload = () => {
    if (downloadUrl) {
      window.open(downloadUrl, '_blank');
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      </DashboardLayout>
    );
  }

  if (error || !document) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-medium text-gray-900">
            {error || 'Document not found'}
          </h2>
          <button
            onClick={() => router.back()}
            className="mt-4 inline-flex items-center text-primary-600 hover:text-primary-500"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go back
          </button>
        </div>
      </DashboardLayout>
    );
  }

  const getStatusBadge = () => {
    switch (document.status) {
      case 'verified':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
            <CheckCircle className="h-4 w-4 mr-1" />
            Verified
          </span>
        );
      case 'needs_review':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
            <AlertCircle className="h-4 w-4 mr-1" />
            Needs Review
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            Processing
          </span>
        );
      case 'extracted':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            Extracted
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
            {document.status}
          </span>
        );
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <button
              onClick={() => router.back()}
              className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </button>
            <div className="flex items-center space-x-3">
              <FileText className="h-8 w-8 text-gray-400" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{document.filename}</h1>
                <p className="text-sm text-gray-500 capitalize">
                  {document.document_type.replace('_', ' ')} • Uploaded{' '}
                  {formatDate(document.uploaded_at)}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {getStatusBadge()}
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Document Preview/Download */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-900">Document</h2>
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleDownload}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </button>
                {downloadUrl && (
                  <a
                    href={downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Open
                  </a>
                )}
              </div>
            </div>

            {/* Document Preview Iframe */}
            {downloadUrl && document.content_type === 'application/pdf' && (
              <div className="border rounded-lg overflow-hidden" style={{ height: '600px' }}>
                <iframe
                  src={downloadUrl}
                  className="w-full h-full"
                  title="Document Preview"
                />
              </div>
            )}

            {/* Image Preview */}
            {downloadUrl && document.content_type?.startsWith('image/') && (
              <div className="border rounded-lg overflow-hidden">
                <img
                  src={downloadUrl}
                  alt={document.filename}
                  className="w-full h-auto"
                />
              </div>
            )}

            {/* Fallback for other types */}
            {downloadUrl &&
              !document.content_type?.includes('pdf') &&
              !document.content_type?.startsWith('image/') && (
                <div className="border-2 border-dashed rounded-lg p-12 text-center">
                  <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">
                    Preview not available for this file type
                  </p>
                  <button
                    onClick={handleDownload}
                    className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download to View
                  </button>
                </div>
              )}
          </div>

          {/* Extracted Data */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-900">Extracted Data</h2>
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleReprocess}
                  disabled={isReprocessing}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  {isReprocessing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Reprocess
                    </>
                  )}
                </button>
                {document.status !== 'verified' && extractedData && (
                  <button
                    onClick={handleVerify}
                    disabled={isVerifying}
                    className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                  >
                    {isVerifying ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Verify
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Confidence Score */}
            {document.extraction_confidence !== null && document.extraction_confidence !== undefined && (
              <div className="mb-4">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-500">Extraction Confidence</span>
                  <span
                    className={`font-medium ${
                      document.extraction_confidence >= 0.85
                        ? 'text-green-600'
                        : document.extraction_confidence >= 0.7
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}
                  >
                    {Math.round(document.extraction_confidence * 100)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      document.extraction_confidence >= 0.85
                        ? 'bg-green-500'
                        : document.extraction_confidence >= 0.7
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${document.extraction_confidence * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Extracted Data Display */}
            {document.status === 'processing' ? (
              <div className="text-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600 mx-auto mb-4" />
                <p className="text-gray-600">Extracting data from document...</p>
                <p className="text-sm text-gray-500 mt-1">
                  This may take a few moments
                </p>
              </div>
            ) : extractedData ? (
              <ExtractionDataView
                data={extractedData}
                isEditing={false}
                onEdit={() => {}}
                editedData={{}}
                setEditedData={() => {}}
              />
            ) : (
              <div className="text-center py-12">
                <FileText className="h-8 w-8 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No extracted data available</p>
                <button
                  onClick={handleReprocess}
                  disabled={isReprocessing}
                  className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
                >
                  {isReprocessing ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Extract Data
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
