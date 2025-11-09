/**
 * Mock API responses that match the Lambda function outputs
 * This allows frontend development before backend deployment
 */

// Generate a realistic UUID
const generateId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

// Mock vendor database (for createVendor storage)
let vendorDatabase = {};

export const mockData = {
  /**
   * POST /vendors - Create new vendor
   */
  createVendor: (data) => {
    const vendorId = generateId();
    const vendor = {
      id: vendorId,
      ...data,
      status: 'submitted',
      onboarding_progress: 0,
      ky3p_assessment_id: `KY3P-${vendorId.substring(0, 8).toUpperCase()}`,
      slp_supplier_id: `SLP-${vendorId.substring(0, 8).toUpperCase()}`,
      created_at: new Date().toISOString()
    };

    vendorDatabase[vendorId] = vendor;

    return new Promise((resolve) => {
      setTimeout(() => resolve(vendor), 500); // Simulate network delay
    });
  },

  /**
   * GET /vendors/{id}/status - Get vendor onboarding status
   */
  getStatus: (vendorId) => {
    const baseStatus = {
      vendor_id: vendorId,
      company_name: vendorDatabase[vendorId]?.company_name || 'Demo Company Inc',
      status: 'under_review',
      onboarding_progress: 65,
      ky3p_assessment_id: `KY3P-${vendorId.substring(0, 8).toUpperCase()}`,
      slp_supplier_id: `SLP-${vendorId.substring(0, 8).toUpperCase()}`,
      created_at: new Date().toISOString(),
      documents: [
        {
          type: 'w9',
          status: 'verified',
          uploaded_at: new Date(Date.now() - 86400000).toISOString() // 1 day ago
        },
        {
          type: 'insurance_certificate',
          status: 'verified',
          uploaded_at: new Date(Date.now() - 43200000).toISOString() // 12 hours ago
        },
        {
          type: 'business_license',
          status: 'processing',
          uploaded_at: new Date(Date.now() - 3600000).toISOString() // 1 hour ago
        }
      ],
      next_steps: [
        'Wait for business license verification to complete',
        'AI risk assessment will run after all documents are verified',
        'Compliance team will review within 24 hours'
      ],
      risk_score: 42, // Include for demo purposes
      timeline: [
        {
          title: 'Business License uploaded',
          timestamp: new Date(Date.now() - 3600000).toISOString()
        },
        {
          title: 'Insurance Certificate verified',
          timestamp: new Date(Date.now() - 43200000).toISOString()
        },
        {
          title: 'W-9 Form verified',
          timestamp: new Date(Date.now() - 86400000).toISOString()
        },
        {
          title: 'Vendor account created',
          timestamp: new Date(Date.now() - 172800000).toISOString()
        }
      ]
    };

    return new Promise((resolve) => {
      setTimeout(() => resolve(baseStatus), 300);
    });
  },

  /**
   * POST /documents/upload - Get presigned URL for document upload
   */
  getUploadUrl: (vendorId, documentType, filename) => {
    const documentId = generateId();
    const response = {
      upload_url: `https://fake-s3-bucket.s3.amazonaws.com/vendors/${vendorId}/${documentType}/${documentId}/${filename}`,
      upload_fields: {
        key: `vendors/${vendorId}/${documentType}/${documentId}/${filename}`,
        'x-amz-meta-vendor-id': vendorId,
        'x-amz-meta-document-type': documentType
      },
      document_id: documentId,
      s3_key: `vendors/${vendorId}/${documentType}/${documentId}/${filename}`,
      expires_in: 3600
    };

    return new Promise((resolve) => {
      setTimeout(() => resolve(response), 200);
    });
  },

  /**
   * POST /vendors/{id}/risk-score - Calculate risk score
   */
  calculateRiskScore: (vendorId) => {
    const riskScore = {
      vendor_id: vendorId,
      overall_score: 42,
      breakdown: {
        financial: 30,
        compliance: 45,
        cyber: 60,
        esg: 25
      },
      risk_level: 'medium',
      sanctions_screening: {
        matches: 0,
        response_time_ms: 347,
        lists_checked: ['OFAC', 'EU', 'UN'],
        screened_at: new Date().toISOString()
      },
      red_flags: [
        'Missing SOC 2 certification',
        'Outdated cyber insurance policy'
      ],
      calculated_at: new Date().toISOString()
    };

    return new Promise((resolve) => {
      setTimeout(() => resolve(riskScore), 800); // Longer delay for "calculation"
    });
  },

  /**
   * GET /vendors/{id}/risk-score - Get existing risk score
   */
  getRiskScore: (vendorId) => {
    const riskScore = {
      vendor_id: vendorId,
      overall_score: 42,
      financial_score: 30,
      compliance_score: 45,
      cybersecurity_score: 60,
      esg_score: 25,
      financial_findings: [
        'Strong revenue growth over past 3 years',
        'Adequate working capital ratio',
        'No recent debt defaults'
      ],
      compliance_findings: [
        'All required licenses verified',
        'Minor discrepancy in insurance coverage dates',
        'GDPR compliance documentation pending'
      ],
      cybersecurity_findings: [
        'SOC 2 Type II certification expired',
        'Cyber insurance policy needs renewal',
        'Strong firewall and intrusion detection systems in place'
      ],
      esg_findings: [
        'Excellent environmental sustainability practices',
        'Strong diversity and inclusion policies',
        'Active community engagement programs'
      ],
      recommendations: [
        'Renew SOC 2 certification within 30 days',
        'Update cyber insurance policy to meet minimum coverage requirements',
        'Submit GDPR compliance documentation',
        'Consider third-party cybersecurity audit'
      ],
      risk_level: 'medium',
      sanctions_screening: {
        matches: 0,
        response_time_ms: 347,
        lists_checked: ['OFAC', 'EU', 'UN'],
        screened_at: new Date().toISOString()
      },
      assessed_at: new Date().toISOString(),
      next_review_date: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString() // 90 days from now
    };

    return new Promise((resolve) => {
      setTimeout(() => resolve(riskScore), 300);
    });
  },

  /**
   * POST /vendors/{id}/approve - Approve/reject vendor
   */
  approveVendor: (vendorId, approvalData) => {
    const response = {
      vendor_id: vendorId,
      status: approvalData.approved ? 'approved' : 'rejected',
      approved: approvalData.approved,
      approved_at: new Date().toISOString(),
      message: `Vendor ${vendorDatabase[vendorId]?.company_name || 'Demo Company'} has been ${approvalData.approved ? 'approved' : 'rejected'}`
    };

    return new Promise((resolve) => {
      setTimeout(() => resolve(response), 500);
    });
  },

  /**
   * Mock file upload to S3 (simulates presigned URL upload)
   */
  uploadToS3: (url, file) => {
    // In real implementation, this would be axios.put(url, file)
    // For mock, just simulate success
    return new Promise((resolve) => {
      setTimeout(() => resolve({ success: true }), 1000);
    });
  },

  /**
   * Upload document (combined helper)
   */
  uploadDocument: (vendorId, documentType, uploadData) => {
    const documentId = generateId();
    const response = {
      document_id: documentId,
      status: 'uploaded',
      message: `${uploadData.filename} uploaded successfully`
    };

    return new Promise((resolve) => {
      setTimeout(() => resolve(response), 1500);
    });
  }
};

// Initialize with a sample vendor for testing
const sampleVendorId = '550e8400-e29b-41d4-a716-446655440000';
vendorDatabase[sampleVendorId] = {
  id: sampleVendorId,
  company_name: 'TechVendor Inc',
  contact_email: 'contact@techvendor.com',
  ein: '12-3456789',
  address: '123 Silicon Valley, CA 94025',
  contact_phone: '+1-650-555-0100',
  status: 'under_review',
  onboarding_progress: 65,
  ky3p_assessment_id: 'KY3P-550E8400',
  slp_supplier_id: 'SLP-550E8400',
  created_at: '2025-11-05T10:30:00Z'
};

// Mock vendors list for GS Dashboard (Using real business data for API testing)
export const mockVendors = [
  {
    id: 'vendor-001',
    company_name: 'Microsoft Corporation',
    contact_email: 'info@microsoft.com',
    ein: '91-1144442',
    address: 'One Microsoft Way, Redmond, WA 98052',
    contact_phone: '+1-425-882-8080',
    status: 'pending',
    risk_score: 78,
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z'
  },
  {
    id: 'vendor-002',
    company_name: 'Apple Inc',
    contact_email: 'contact@apple.com',
    ein: '94-2404110',
    address: 'One Apple Park Way, Cupertino, CA 95014',
    contact_phone: '+1-408-996-1010',
    status: 'approved',
    risk_score: 85,
    created_at: '2024-01-10T14:20:00Z',
    updated_at: '2024-01-12T09:15:00Z'
  },
  {
    id: 'vendor-003',
    company_name: 'Amazon.com Inc',
    contact_email: 'sales@amazon.com',
    ein: '91-1646860',
    address: '410 Terry Avenue North, Seattle, WA 98109',
    contact_phone: '+1-206-266-1000',
    status: 'approved',
    risk_score: 92,
    created_at: '2024-01-08T08:45:00Z',
    updated_at: '2024-01-09T16:30:00Z'
  },
  {
    id: 'vendor-004',
    company_name: 'Tesla Inc',
    contact_email: 'info@tesla.com',
    ein: '91-2197729',
    address: '1 Tesla Road, Austin, TX 78725',
    contact_phone: '+1-512-516-8177',
    status: 'pending',
    risk_score: 82,
    created_at: '2024-01-14T11:00:00Z',
    updated_at: '2024-01-14T11:00:00Z'
  },
  {
    id: 'vendor-005',
    company_name: 'Northwind Traders',
    contact_email: 'contact@northwind.fake',
    ein: '123456789',
    address: '123 Unknown Street, Gotham City, NY 00000',
    contact_phone: '+1-555-000-0000',
    status: 'rejected',
    risk_score: 45,
    created_at: '2024-01-05T13:20:00Z',
    updated_at: '2024-01-07T10:45:00Z'
  },
  {
    id: 'vendor-006',
    company_name: 'Acme Logistics LLC',
    contact_email: 'support@acme-logistics.invalid',
    ein: '98-7654321',
    address: '789 Desert Road, Nowhere, NV 89000',
    contact_phone: '+1-999-123-4567',
    status: 'approved',
    risk_score: 88,
    created_at: '2024-01-03T09:10:00Z',
    updated_at: '2024-01-04T15:20:00Z'
  },
  {
    id: 'vendor-007',
    company_name: 'Quantum Apex Solutions',
    contact_email: 'hello@quantum-apex.biz',
    ein: '00-1234567',
    address: '456 Industrial Ave, Metropolis, KS 66002',
    contact_phone: '+1-312-555-7890',
    status: 'pending',
    risk_score: 65,
    created_at: '2024-01-16T15:45:00Z',
    updated_at: '2024-01-16T15:45:00Z'
  },
  {
    id: 'vendor-008',
    company_name: 'Skyline Media Group',
    contact_email: 'info@skylinemedia.co',
    ein: '45-0000001',
    address: '88 Riverside Drive, Harbour City, FL 33100',
    contact_phone: '+1-718-000-1122',
    status: 'approved',
    risk_score: 90,
    created_at: '2023-12-28T10:30:00Z',
    updated_at: '2024-01-02T14:15:00Z'
  }
];

export default mockData;
