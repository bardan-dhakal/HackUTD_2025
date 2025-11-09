import { useState } from 'react'
import { GoogleGenAI } from '@google/genai'

const RejectWithFeedback = ({ vendor, verificationResults, onClose, onReject }) => {
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')

  const generateFeedback = async () => {
    setLoading(true)
    setError('')

    try {
      const apiKey = import.meta.env.VITE_GEMINI_API_KEY
      
      if (!apiKey) {
        throw new Error('Gemini API key not found')
      }

      // Initialize the new Gemini AI SDK
      const ai = new GoogleGenAI({ apiKey })

      // Prepare vendor data for analysis
      const vendorAnalysis = {
        company: vendor.company_name,
        risk_score: vendor.risk_score,
        email: vendor.contact_email,
        phone: vendor.contact_phone,
        address: vendor.address,
        ein: vendor.ein,
        verification_results: verificationResults
      }

      const prompt = `You are an expert vendor relationship manager at Goldman Sachs. A vendor application has been rejected, but we want to maintain a positive relationship and help them improve for future applications.

Vendor Information:
- Company: ${vendorAnalysis.company}
- Risk Score: ${vendorAnalysis.risk_score}/100
- Email: ${vendorAnalysis.email}
- Phone: ${vendorAnalysis.phone}
- Address: ${vendorAnalysis.address}
- EIN: ${vendorAnalysis.ein}

Verification Results:
${JSON.stringify(vendorAnalysis.verification_results, null, 2)}

Please generate a professional, constructive rejection letter that:
1. Thanks them for their interest in partnering with Goldman Sachs
2. Clearly explains the specific reasons for rejection (based on low risk score, failed verifications, or compliance issues)
3. Provides actionable recommendations on how to improve each issue
4. Encourages them to reapply after addressing the concerns
5. Maintains a warm, professional tone that preserves the relationship

Keep it concise (3-4 paragraphs), professional, and helpful. Focus on what they can control and improve.`

      // Generate content using the new SDK
      const response = await ai.models.generateContent({
        model: 'gemini-2.0-flash',
        contents: prompt
      })

      const text = response.text

      if (text) {
        setFeedback(text)
      } else {
        throw new Error('No feedback generated from API')
      }

    } catch (err) {
      console.error('Gemini API error:', err)
      setError(`Failed to generate feedback: ${err.message || 'Please try again.'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleReject = () => {
    onReject(feedback)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">
              Reject with AI-Generated Feedback
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Use Gemini AI to generate constructive feedback for {vendor.company_name}
          </p>
        </div>

        <div className="p-6">
          {/* Error Message */}
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          {/* Generate Button */}
          {!feedback && (
            <div className="text-center py-8">
              <div className="mb-4">
                <svg className="w-16 h-16 mx-auto text-gs-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Generate Personalized Feedback
              </h3>
              <p className="text-gray-600 mb-6">
                Gemini AI will analyze the vendor's risk score, verification results, and compliance data to create a constructive rejection letter.
              </p>
              <button
                onClick={generateFeedback}
                disabled={loading}
                className="btn-primary bg-gs-blue hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating Feedback...
                  </span>
                ) : (
                  '✨ Generate AI Feedback'
                )}
              </button>
            </div>
          )}

          {/* Generated Feedback */}
          {feedback && (
            <div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Generated Feedback Letter
                  <span className="text-gray-500 ml-2 font-normal">(You can edit before sending)</span>
                </label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  rows={15}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gs-blue focus:border-transparent outline-none"
                />
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                <button
                  onClick={generateFeedback}
                  disabled={loading}
                  className="text-gs-blue hover:text-blue-700 font-medium flex items-center"
                >
                  🔄 Regenerate
                </button>
                <div className="flex gap-3">
                  <button
                    onClick={onClose}
                    className="px-6 py-2 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleReject}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium"
                  >
                    Send Rejection with Feedback
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default RejectWithFeedback