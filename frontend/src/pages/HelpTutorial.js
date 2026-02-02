import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  BookOpen, 
  Users, 
  ShoppingCart, 
  Package, 
  BarChart3, 
  HelpCircle,
  Phone,
  Mail,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowRight,
  Lightbulb,
  PlayCircle,
  FileText,
  Calculator,
  Shield,
  Clock
} from 'lucide-react';

const HelpTutorial = () => {
  const [activeTab, setActiveTab] = useState('getting-started');

  const tutorials = [
    {
      id: 'login',
      title: 'Logging In',
      icon: Shield,
      steps: [
        'Open your web browser and navigate to the PRIVITY application URL',
        'Enter your registered Email Address',
        'Enter your Password',
        'Click "Sign In"',
        'On first login, accept the User Agreement'
      ]
    },
    {
      id: 'clients',
      title: 'Adding a Client',
      icon: Users,
      steps: [
        'Click "Clients" in the sidebar menu',
        'Click "Add Client" button (top right)',
        'Select Client Type (Proprietor, Partnership, Company, etc.)',
        'Fill in required details: Name, PAN, Mobile, Email',
        'Enter Bank Details: Account Number, IFSC, Bank Name',
        'Enter Demat Details: DP ID, Client ID, BO ID',
        'Upload required documents (Aadhar, PAN Card)',
        'Click "Submit for Approval"'
      ]
    },
    {
      id: 'booking',
      title: 'Creating a Booking',
      icon: ShoppingCart,
      steps: [
        'Click "Bookings" in the sidebar',
        'Click "Create Booking" button',
        'Select an approved Client from dropdown',
        'Select the Stock to book',
        'Enter Quantity (number of shares)',
        'Enter Selling Price per share',
        'Review the Landing Price and Revenue preview',
        'Click "Create Booking" to submit'
      ]
    },
    {
      id: 'inventory',
      title: 'Checking Inventory',
      icon: Package,
      steps: [
        'Click "Inventory" in the sidebar',
        'View available stocks with quantities',
        'Check "Available Qty" before creating bookings',
        'Note "Blocked Qty" for pending bookings',
        'Landing Price (LP) is the buying price for calculations'
      ]
    },
    {
      id: 'reports',
      title: 'Generating Reports',
      icon: BarChart3,
      steps: [
        'Click "Reports" in the sidebar',
        'Select your desired date range',
        'Apply filters (Stock, Client, Status)',
        'View the profit/loss summary',
        'Click "Export Excel" or "Export PDF" to download'
      ]
    }
  ];

  const faqs = [
    {
      question: "I forgot my password. What should I do?",
      answer: "Click 'Forgot Password' on the login page and follow the email instructions. Alternatively, contact PE Desk at pe@smifs.com for assistance."
    },
    {
      question: "Why can't I create a booking for a client?",
      answer: "The client must be in 'Approved' status. Check if the client is pending approval from PE Desk. Only approved clients can have bookings created."
    },
    {
      question: "How do I know if PE support is available?",
      answer: "Look at the status indicator in the sidebar - Green means PE Support is available for immediate help, Red means they are offline (leave a message)."
    },
    {
      question: "Can I edit a booking after creation?",
      answer: "Bookings can only be edited before client confirmation. After confirmation, contact PE Desk for any changes or cancellations."
    },
    {
      question: "Why is my booking showing 'Loss'?",
      answer: "If the selling price is less than the landing price, it's considered a loss booking. These require additional approval from PE Desk before processing."
    },
    {
      question: "How do I export data?",
      answer: "Most pages have 'Export Excel' or 'Export PDF' buttons in the top right corner. Click to download the data in your preferred format."
    },
    {
      question: "What is the difference between WAP and LP?",
      answer: "WAP (Weighted Average Price) is the actual cost price visible only to PE Level users. LP (Landing Price) is the customer-facing price used for all booking calculations."
    },
    {
      question: "How is revenue calculated?",
      answer: "Revenue = (Selling Price - Landing Price) × Quantity. For example: If you sell 100 shares at ₹150 with LP of ₹120, Revenue = (150-120) × 100 = ₹3,000"
    },
    {
      question: "What happens after I create a booking?",
      answer: "The booking goes through: Created → Client Confirmation → PE Approval → DP Transfer → Completed. You'll receive notifications at each stage."
    },
    {
      question: "How do I track payment status?",
      answer: "Go to the Finance section or view the booking details. Payment status shows as Unpaid, Partial, or Paid with the recorded amounts."
    }
  ];

  const statusGuide = [
    { status: 'Approved', color: 'bg-green-500', description: 'Client/Booking is active and ready' },
    { status: 'Pending', color: 'bg-yellow-500', description: 'Awaiting approval or action' },
    { status: 'Rejected', color: 'bg-red-500', description: 'Denied - check comments for reason' },
    { status: 'Completed', color: 'bg-blue-500', description: 'Transaction fully processed' }
  ];

  return (
    <div className="p-4 md:p-6 lg:p-8 page-enter" data-testid="help-tutorial-page">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
            <BookOpen className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <h1 className="text-4xl font-bold">Help & Tutorial</h1>
        </div>
        <p className="text-muted-foreground text-base">
          Learn how to use PRIVITY effectively with step-by-step guides and answers to common questions
        </p>
      </div>

      {/* Quick Contact Card */}
      <Card className="mb-6 bg-gradient-to-r from-emerald-500 to-teal-500 text-white border-0">
        <CardContent className="py-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h3 className="font-semibold text-lg">Need immediate help?</h3>
              <p className="text-emerald-100">Contact PE Desk for support</p>
            </div>
            <div className="flex gap-4">
              <a href="mailto:pe@smifs.com" className="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-colors">
                <Mail className="h-4 w-4" />
                pe@smifs.com
              </a>
              <a href="tel:9088963000" className="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-colors">
                <Phone className="h-4 w-4" />
                9088963000
              </a>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-2 md:grid-cols-4 gap-2 h-auto p-1 bg-muted">
          <TabsTrigger value="getting-started" className="flex items-center gap-2 py-2" data-testid="tab-getting-started">
            <PlayCircle className="h-4 w-4" />
            <span className="hidden sm:inline">Getting Started</span>
            <span className="sm:hidden">Start</span>
          </TabsTrigger>
          <TabsTrigger value="tutorials" className="flex items-center gap-2 py-2" data-testid="tab-tutorials">
            <FileText className="h-4 w-4" />
            Tutorials
          </TabsTrigger>
          <TabsTrigger value="faq" className="flex items-center gap-2 py-2" data-testid="tab-faq">
            <HelpCircle className="h-4 w-4" />
            FAQ
          </TabsTrigger>
          <TabsTrigger value="reference" className="flex items-center gap-2 py-2" data-testid="tab-reference">
            <Lightbulb className="h-4 w-4" />
            Reference
          </TabsTrigger>
        </TabsList>

        {/* Getting Started Tab */}
        <TabsContent value="getting-started" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PlayCircle className="h-5 w-5 text-emerald-500" />
                Welcome to PRIVITY
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <p className="text-muted-foreground">
                PRIVITY is your complete Share Booking System for managing clients, bookings, inventory, and financial reports. 
                Follow this quick guide to get started.
              </p>

              {/* Step by Step */}
              <div className="grid gap-4">
                <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
                  <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-bold">1</div>
                  <div>
                    <h4 className="font-semibold">Login to your account</h4>
                    <p className="text-sm text-muted-foreground">Use your email and password provided by your administrator. On first login, accept the user agreement.</p>
                  </div>
                </div>
                <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
                  <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-bold">2</div>
                  <div>
                    <h4 className="font-semibold">Navigate using the sidebar</h4>
                    <p className="text-sm text-muted-foreground">The sidebar menu shows all available modules as icon buttons. Click any button to access that section.</p>
                  </div>
                </div>
                <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
                  <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-bold">3</div>
                  <div>
                    <h4 className="font-semibold">Add or select a client</h4>
                    <p className="text-sm text-muted-foreground">Go to Clients to add new clients or view existing ones. Clients need PE Desk approval before bookings.</p>
                  </div>
                </div>
                <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
                  <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-bold">4</div>
                  <div>
                    <h4 className="font-semibold">Create your first booking</h4>
                    <p className="text-sm text-muted-foreground">Go to Bookings → Create Booking. Select client, stock, enter quantity and selling price, then submit.</p>
                  </div>
                </div>
                <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
                  <div className="flex-shrink-0 w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center font-bold">5</div>
                  <div>
                    <h4 className="font-semibold">Track and manage</h4>
                    <p className="text-sm text-muted-foreground">Use Dashboard for overview, Reports for analytics, and Finance for payment tracking.</p>
                  </div>
                </div>
              </div>

              {/* Interface Overview */}
              <div className="mt-6 p-4 border rounded-lg bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
                <h4 className="font-semibold mb-3">Understanding the Interface</h4>
                <div className="grid md:grid-cols-2 gap-4 text-sm">
                  <div className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 text-emerald-500 mt-0.5" />
                    <div><strong>Sidebar (Left):</strong> Navigation menu with icon buttons</div>
                  </div>
                  <div className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 text-emerald-500 mt-0.5" />
                    <div><strong>Main Area (Center):</strong> Current page content</div>
                  </div>
                  <div className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 text-emerald-500 mt-0.5" />
                    <div><strong>PE Status:</strong> Green = Online, Red = Offline</div>
                  </div>
                  <div className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 text-emerald-500 mt-0.5" />
                    <div><strong>Notifications:</strong> Bell icon shows alerts</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tutorials Tab */}
        <TabsContent value="tutorials" className="space-y-4">
          {tutorials.map((tutorial) => {
            const Icon = tutorial.icon;
            return (
              <Card key={tutorial.id} data-testid={`tutorial-${tutorial.id}`}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Icon className="h-5 w-5 text-emerald-500" />
                    {tutorial.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ol className="space-y-2">
                    {tutorial.steps.map((step, idx) => (
                      <li key={idx} className="flex gap-3 items-start">
                        <span className="flex-shrink-0 w-6 h-6 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-full flex items-center justify-center text-sm font-medium">
                          {idx + 1}
                        </span>
                        <span className="text-sm pt-0.5">{step}</span>
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>

        {/* FAQ Tab */}
        <TabsContent value="faq">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-purple-500" />
                Frequently Asked Questions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="w-full">
                {faqs.map((faq, idx) => (
                  <AccordionItem key={idx} value={`faq-${idx}`} data-testid={`faq-item-${idx}`}>
                    <AccordionTrigger className="text-left hover:no-underline">
                      <span className="flex items-center gap-2">
                        <HelpCircle className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        {faq.question}
                      </span>
                    </AccordionTrigger>
                    <AccordionContent className="text-muted-foreground pl-6">
                      {faq.answer}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reference Tab */}
        <TabsContent value="reference" className="space-y-6">
          {/* Status Guide */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-amber-500" />
                Status Indicators
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                {statusGuide.map((item) => (
                  <div key={item.status} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                    <div className={`w-4 h-4 rounded-full ${item.color}`}></div>
                    <div>
                      <div className="font-medium">{item.status}</div>
                      <div className="text-sm text-muted-foreground">{item.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Revenue Formula */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5 text-blue-500" />
                Revenue Calculation
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-gradient-to-r from-gray-900 to-gray-800 text-white rounded-lg text-center font-mono text-lg">
                Revenue = (Selling Price - Landing Price) × Quantity
              </div>
              <div className="p-4 bg-muted/50 rounded-lg">
                <h4 className="font-medium mb-2">Example:</h4>
                <ul className="space-y-1 text-sm">
                  <li>• Selling Price: ₹150</li>
                  <li>• Landing Price: ₹120</li>
                  <li>• Quantity: 100 shares</li>
                  <li className="font-bold text-emerald-600">• Revenue: (150 - 120) × 100 = ₹3,000</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Booking Workflow */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-orange-500" />
                Booking Workflow
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap items-center justify-center gap-2 p-4 bg-muted/50 rounded-lg">
                <Badge variant="outline" className="py-2 px-3">Created</Badge>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <Badge variant="outline" className="py-2 px-3">Client Confirm</Badge>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <Badge variant="outline" className="py-2 px-3 bg-amber-50 border-amber-200">PE Approval</Badge>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <Badge variant="outline" className="py-2 px-3">DP Transfer</Badge>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                <Badge variant="outline" className="py-2 px-3 bg-emerald-50 border-emerald-200">Completed</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Do's and Don'ts */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="border-emerald-200 dark:border-emerald-800">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-emerald-600">
                  <CheckCircle className="h-5 w-5" />
                  Do's
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    Verify client details before booking
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    Check available inventory first
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    Double-check quantity and price
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    Follow up on pending confirmations
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    Keep client documents updated
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="border-red-200 dark:border-red-800">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-red-600">
                  <XCircle className="h-5 w-5" />
                  Don'ts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-start gap-2">
                    <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                    Create duplicate bookings
                  </li>
                  <li className="flex items-start gap-2">
                    <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                    Book more than available quantity
                  </li>
                  <li className="flex items-start gap-2">
                    <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                    Skip client confirmation step
                  </li>
                  <li className="flex items-start gap-2">
                    <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                    Share your login credentials
                  </li>
                  <li className="flex items-start gap-2">
                    <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                    Modify completed bookings
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default HelpTutorial;
