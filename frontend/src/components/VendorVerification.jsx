import { useState, useEffect } from 'react'

const VendorVerification = ({ vendor, onVerificationComplete }) => {
  const [verificationResults, setVerificationResults] = useState({
    email_domain: { status: 'pending', message: 'Checking...' },
    phone_format: { status: 'pending', message: 'Validating...' },
    ein_format: { status: 'pending', message: 'Validating...' },
    address: { status: 'pending', message: 'Verifying...' },
    business_registry: { status: 'pending', message: 'Searching...' }
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    runVerifications()
  }, [vendor])

  const runVerifications = async () => {
    setLoading(true)
    
    // Run all verifications in parallel
    const [emailCheck, phoneCheck, einCheck, addressCheck, businessCheck] = await Promise.all([
      verifyEmailDomain(vendor.contact_email),
      validatePhoneFormat(vendor.contact_phone),
      validateEINFormat(vendor.ein),
      verifyAddress(vendor.address),
      checkBusinessRegistry(vendor.company_name)
    ])
    
    const results = {
      email_domain: emailCheck,
      phone_format: phoneCheck,
      ein_format: einCheck,
      address: addressCheck,
      business_registry: businessCheck
    }
    
    setVerificationResults(results)
    
    // Pass results to parent component if callback provided
    if (onVerificationComplete) {
      onVerificationComplete(results)
    }
    
    setLoading(false)
  }

  const verifyEmailDomain = async (email) => {
    if (!email) {
      return { status: 'warning', message: 'No email provided' }
    }

    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      return {
        status: 'failed',
        message: 'Invalid email format'
      }
    }

    try {
      // Check if domain has MX records using Google DNS (free, no API key)
      const domain = email.split('@')[1]
      const response = await fetch(
        `https://dns.google/resolve?name=${domain}&type=MX`
      )
      const data = await response.json()
      
      if (data.Status === 0 && data.Answer && data.Answer.length > 0) {
        return {
          status: 'verified',
          message: `Valid email domain - MX records found for ${domain}`,
          details: data
        }
      } else {
        return {
          status: 'failed',
          message: `No mail server found for domain ${domain}`
        }
      }
    } catch (error) {
      console.error('Email verification error:', error)
      return {
        status: 'error',
        message: 'Email verification service unavailable'
      }
    }
  }

  const validatePhoneFormat = async (phone) => {
    if (!phone) {
      return { status: 'warning', message: 'No phone number provided' }
    }
    
    try {
      const apiKey = import.meta.env.VITE_ABSTRACT_API_KEY
      
      const response = await fetch(
        `https://phonevalidation.abstractapi.com/v1/?api_key=${apiKey}&phone=${encodeURIComponent(phone)}`
      )
      const data = await response.json()
      
      if (data.valid) {
        return {
          status: 'verified',
          message: `Valid ${data.country?.name || ''} phone - ${data.format?.international || phone}`,
          details: data
        }
      } else {
        return {
          status: 'warning',
          message: 'Phone number format could not be verified'
        }
      }
    } catch (error) {
      console.error('Phone verification error:', error)
      // Fallback to regex validation
      const phoneRegex = /^[\+]?[1]?[-.\s]?[(]?[0-9]{3}[)]?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$/
      
      if (phoneRegex.test(phone)) {
        return {
          status: 'verified',
          message: 'Valid US phone format'
        }
      } else {
        return {
          status: 'warning',
          message: 'Invalid phone format'
        }
      }
    }
  }

  const validateEINFormat = (ein) => {
    if (!ein) {
      return { status: 'warning', message: 'No EIN provided' }
    }

    const einRegex = /^\d{2}-\d{7}$/
    
    if (einRegex.test(ein)) {
      return {
        status: 'verified',
        message: 'Valid EIN format (XX-XXXXXXX)'
      }
    } else {
      return {
        status: 'failed',
        message: 'Invalid EIN format - should be XX-XXXXXXX'
      }
    }
  }

  const verifyAddress = async (address) => {
    if (!address) {
      return { status: 'warning', message: 'No address provided' }
    }

    try {
      // Use Nominatim (OpenStreetMap) - Free, no API key needed
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}`,
        {
          headers: {
            'User-Agent': 'GoldmanSachs-VendorOnboarding/1.0'
          }
        }
      )
      const data = await response.json()
      
      if (data && data.length > 0) {
        const result = data[0]
        
        return {
          status: 'verified',
          message: `Address verified: ${result.display_name}`,
          details: {
            lat: result.lat,
            lon: result.lon,
            type: result.type,
            importance: result.importance
          }
        }
      } else {
        return {
          status: 'warning',
          message: 'Address could not be geocoded'
        }
      }
    } catch (error) {
      console.error('Address verification error:', error)
      return {
        status: 'error',
        message: 'Address verification service unavailable'
      }
    }
  }

  const checkBusinessRegistry = async (companyName) => {
    if (!companyName) {
      return { status: 'warning', message: 'No company name provided' }
    }

    try {
      // OpenCorporates API - Free tier
      const response = await fetch(
        `https://api.opencorporates.com/v0.4/companies/search?q=${encodeURIComponent(companyName)}&jurisdiction_code=us&order=score`,
        {
          headers: {
            'User-Agent': 'GoldmanSachs-VendorOnboarding/1.0'
          }
        }
      )
      const data = await response.json()
      
      if (data.results && data.results.companies && data.results.companies.length > 0) {
        const topMatch = data.results.companies[0].company
        const isActive = topMatch.current_status === 'Active'
        
        return {
          status: isActive ? 'verified' : 'warning',
          message: isActive 
            ? `Found: ${topMatch.name} (${topMatch.current_status})` 
            : `Found: ${topMatch.name} (${topMatch.current_status || 'Unknown Status'})`,
          details: {
            name: topMatch.name,
            jurisdiction: topMatch.jurisdiction_code,
            status: topMatch.current_status,
            incorporation_date: topMatch.incorporation_date
          }
        }
      } else {
        return {
          status: 'warning',
          message: 'No business registration found in OpenCorporates database'
        }
      }
    } catch (error) {
      console.error('Business registry error:', error)
      return {
        status: 'error',
        message: 'Business registry check unavailable'
      }
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'verified':
        return '✅'
      case 'warning':
        return '⚠️'
      case 'failed':
        return '❌'
      case 'error':
        return '🔴'
      default:
        return '⏳'
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'verified':
        return 'bg-green-50 border-green-200 text-green-800'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      case 'failed':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'error':
        return 'bg-gray-50 border-gray-200 text-gray-800'
      default:
        return 'bg-blue-50 border-blue-200 text-blue-800'
    }
  }

  const getOverallStatus = () => {
    const statuses = Object.values(verificationResults).map(r => r.status)
    
    if (statuses.every(s => s === 'verified')) {
      return { color: 'bg-green-100 text-green-800', text: '✅ All Checks Passed', icon: '✅' }
    } else if (statuses.some(s => s === 'failed')) {
      return { color: 'bg-red-100 text-red-800', text: '❌ Verification Issues Found', icon: '❌' }
    } else {
      return { color: 'bg-yellow-100 text-yellow-800', text: '⚠️ Review Required', icon: '⚠️' }
    }
  }

  const overallStatus = getOverallStatus()

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-900">Identity Verification</h3>
          <p className="text-sm text-gray-600 mt-1">Automated vendor legitimacy checks</p>
        </div>
        {loading && (
          <div className="flex items-center text-sm text-gray-600">
            <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Verifying...
          </div>
        )}
        {!loading && (
          <button 
            onClick={runVerifications}
            className="text-sm text-gs-blue hover:text-blue-700 font-medium flex items-center"
          >
            🔄 Re-verify
          </button>
        )}
      </div>

      <div className="space-y-3">
        {/* Email Domain */}
        <div className={`border rounded-lg p-3 ${getStatusColor(verificationResults.email_domain.status)}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center mb-1">
                <span className="text-lg mr-2">{getStatusIcon(verificationResults.email_domain.status)}</span>
                <h4 className="font-semibold">Email Domain Verification</h4>
              </div>
              <p className="text-sm ml-7">{verificationResults.email_domain.message}</p>
              <p className="text-xs ml-7 mt-1 opacity-75">Email: {vendor.contact_email}</p>
            </div>
          </div>
        </div>

        {/* Phone Number */}
        <div className={`border rounded-lg p-3 ${getStatusColor(verificationResults.phone_format.status)}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center mb-1">
                <span className="text-lg mr-2">{getStatusIcon(verificationResults.phone_format.status)}</span>
                <h4 className="font-semibold">Phone Number Validation</h4>
              </div>
              <p className="text-sm ml-7">{verificationResults.phone_format.message}</p>
              <p className="text-xs ml-7 mt-1 opacity-75">Phone: {vendor.contact_phone || 'N/A'}</p>
            </div>
          </div>
        </div>

        {/* EIN Format */}
        <div className={`border rounded-lg p-3 ${getStatusColor(verificationResults.ein_format.status)}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center mb-1">
                <span className="text-lg mr-2">{getStatusIcon(verificationResults.ein_format.status)}</span>
                <h4 className="font-semibold">EIN Format Verification</h4>
              </div>
              <p className="text-sm ml-7">{verificationResults.ein_format.message}</p>
              <p className="text-xs ml-7 mt-1 opacity-75">EIN: {vendor.ein}</p>
            </div>
          </div>
        </div>

        {/* Address Verification */}
        <div className={`border rounded-lg p-3 ${getStatusColor(verificationResults.address.status)}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center mb-1">
                <span className="text-lg mr-2">{getStatusIcon(verificationResults.address.status)}</span>
                <h4 className="font-semibold">Business Address Validation</h4>
              </div>
              <p className="text-sm ml-7">{verificationResults.address.message}</p>
              <p className="text-xs ml-7 mt-1 opacity-75">{vendor.address || 'N/A'}</p>
            </div>
          </div>
        </div>

        {/* Business Registry */}
        <div className={`border rounded-lg p-3 ${getStatusColor(verificationResults.business_registry.status)}`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center mb-1">
                <span className="text-lg mr-2">{getStatusIcon(verificationResults.business_registry.status)}</span>
                <h4 className="font-semibold">Business Registry Check</h4>
              </div>
              <p className="text-sm ml-7">{verificationResults.business_registry.message}</p>
              <p className="text-xs ml-7 mt-1 opacity-75">Searched: {vendor.company_name}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Overall Verification Status */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Overall Verification Status:</span>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${overallStatus.color}`}>
            {overallStatus.text}
          </span>
        </div>
      </div>
    </div>
  )
}

export default VendorVerification

