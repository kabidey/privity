import { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import api from '../utils/api';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { 
  Plus, Pencil, Trash2, Search, Upload, Download, RefreshCw, 
  TrendingUp, Building2, Calendar, Percent, Shield, Calculator,
  FileSpreadsheet, ChevronLeft, ChevronRight, Eye, Check
} from 'lucide-react';

const INSTRUMENT_TYPES = [
  { value: 'NCD', label: 'Non-Convertible Debenture' },
  { value: 'BOND', label: 'Bond' },
  { value: 'GSEC', label: 'Government Security' },
  { value: 'TBILL', label: 'Treasury Bill' },
  { value: 'CP', label: 'Commercial Paper' },
  { value: 'CD', label: 'Certificate of Deposit' },
];

const COUPON_FREQUENCIES = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'semi_annual', label: 'Semi-Annual' },
  { value: 'annual', label: 'Annual' },
  { value: 'zero_coupon', label: 'Zero Coupon' },
];

const DAY_COUNT_CONVENTIONS = [
  { value: '30/360', label: '30/360' },
  { value: 'ACT/ACT', label: 'Actual/Actual' },
  { value: 'ACT/360', label: 'Actual/360' },
  { value: 'ACT/365', label: 'Actual/365' },
];

const CREDIT_RATINGS = [
  'AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-',
  'BBB+', 'BBB', 'BBB-', 'BB', 'B', 'C', 'D', 'UNRATED'
];

const FISecurityMaster = () => {
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false);
  const [calcDialogOpen, setCalcDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [editingInstrument, setEditingInstrument] = useState(null);
  const [selectedInstrument, setSelectedInstrument] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [pagination, setPagination] = useState({ skip: 0, limit: 25, total: 0 });
  const [filters, setFilters] = useState({
    instrument_type: '',
    credit_rating: '',
  });

  // NSDL Search State
  const [nsdlSearchOpen, setNsdlSearchOpen] = useState(false);
  const [nsdlSearchQuery, setNsdlSearchQuery] = useState('');
  const [nsdlSearchType, setNsdlSearchType] = useState('all');
  const [nsdlSearchResults, setNsdlSearchResults] = useState([]);
  const [nsdlSearching, setNsdlSearching] = useState(false);
  const [nsdlImporting, setNsdlImporting] = useState({});

  const [formData, setFormData] = useState({
    isin: '',
    instrument_type: 'NCD',
    issuer_name: '',
    issuer_code: '',
    face_value: '1000',
    issue_date: '',
    maturity_date: '',
    coupon_rate: '',
    coupon_frequency: 'annual',
    day_count_convention: 'ACT/365',
    credit_rating: 'UNRATED',
    rating_agency: '',
    current_market_price: '',
    is_callable: false,
    call_date: '',
    call_price: '',
    is_puttable: false,
    put_date: '',
    put_price: '',
    lot_size: '1',
  });

  const [calcData, setCalcData] = useState({
    isin: '',
    clean_price: '',
    settlement_date: new Date().toISOString().split('T')[0],
    target_ytm: '',
  });

  const [calcResult, setCalcResult] = useState(null);
  const [importingPublicData, setImportingPublicData] = useState(false);

  const { isPEDesk, isPEManager, isPELevel } = useCurrentUser();

  const handleImportPublicData = async () => {
    try {
      setImportingPublicData(true);
      toast.info('Starting multi-source import from NSDL, IndiaBonds, Smest...');
      
      // Use the new multi-source import endpoint
      const response = await api.post('/fixed-income/instruments/import-all-sources');
      const stats = response.data.statistics;
      
      toast.success(
        `Import completed! Sources: ${stats.sources?.join(', ')}. Imported: ${stats.imported}, Updated: ${stats.updated}. Total scraped: ${stats.total_scraped}`
      );
      
      if (stats.errors_count > 0) {
        toast.warning(`${stats.errors_count} errors occurred. Check console for details.`);
        console.log('Import errors:', stats.sample_errors);
      }
      
      fetchInstruments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import from sources');
    } finally {
      setImportingPublicData(false);
    }
  };

  // NSDL Search Functions
  const handleNsdlSearch = async () => {
    if (!nsdlSearchQuery || nsdlSearchQuery.length < 2) {
      toast.error('Please enter at least 2 characters to search');
      return;
    }
    try {
      setNsdlSearching(true);
      const params = new URLSearchParams({
        query: nsdlSearchQuery,
        search_type: nsdlSearchType,
        limit: '50',
        live_lookup: 'true'  // Enable live web lookup
      });
      const response = await api.get(`/fixed-income/instruments/nsdl-search?${params}`);
      setNsdlSearchResults(response.data.results || []);
      
      // Check if live lookup was attempted
      if (response.data.live_lookup_attempted) {
        const liveLookup = response.data.live_lookup_result;
        if (liveLookup?.success && liveLookup?.newly_imported) {
          toast.success(`Live lookup found and imported: ${response.data.results[0]?.issuer_name || nsdlSearchQuery}`, {
            duration: 5000,
            description: `Sources: ${liveLookup.sources_found?.join(', ') || 'Web'}`
          });
          fetchInstruments(); // Refresh the list
        } else if (!liveLookup?.success && response.data.results?.length === 0) {
          toast.info('No instruments found locally. Live web lookup attempted but no data found.', {
            duration: 4000
          });
        }
      } else if (response.data.results?.length === 0) {
        toast.info('No instruments found matching your search');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Search failed');
    } finally {
      setNsdlSearching(false);
    }
  };

  const handleNsdlImport = async (isin) => {
    try {
      setNsdlImporting(prev => ({ ...prev, [isin]: true }));
      const response = await api.post(`/fixed-income/instruments/nsdl-import/${isin}`);
      toast.success(`Imported ${isin}: ${response.data.instrument?.issuer_name}`);
      // Update the result to show as imported
      setNsdlSearchResults(prev => prev.map(r => 
        r.isin === isin ? { ...r, already_imported: true, can_import: false } : r
      ));
      fetchInstruments();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to import ${isin}`);
    } finally {
      setNsdlImporting(prev => ({ ...prev, [isin]: false }));
    }
  };

  const handleNsdlImportAll = async () => {
    const importable = nsdlSearchResults.filter(r => r.can_import);
    if (importable.length === 0) {
      toast.info('All instruments are already imported');
      return;
    }
    try {
      setNsdlSearching(true);
      const isins = importable.map(r => r.isin);
      const response = await api.post('/fixed-income/instruments/nsdl-import-multiple', isins);
      toast.success(`Import complete: ${response.data.successful} succeeded, ${response.data.failed} failed`);
      setNsdlSearchResults(prev => prev.map(r => ({ ...r, already_imported: true, can_import: false })));
      fetchInstruments();
    } catch (error) {
      toast.error('Bulk import failed');
    } finally {
      setNsdlSearching(false);
    }
  };

  const fetchInstruments = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: pagination.skip.toString(),
        limit: pagination.limit.toString(),
      });
      
      if (filters.instrument_type) params.append('instrument_type', filters.instrument_type);
      if (filters.credit_rating) params.append('credit_rating', filters.credit_rating);
      if (activeTab !== 'all') params.append('instrument_type', activeTab);

      const response = await api.get(`/fixed-income/instruments?${params}`);
      setInstruments(response.data.instruments || []);
      setPagination(prev => ({ ...prev, total: response.data.total || 0 }));
    } catch (error) {
      console.error('Error fetching instruments:', error);
      toast.error('Failed to load instruments');
    } finally {
      setLoading(false);
    }
  }, [pagination.skip, pagination.limit, filters, activeTab]);

  useEffect(() => {
    fetchInstruments();
  }, [fetchInstruments]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        face_value: parseFloat(formData.face_value),
        coupon_rate: parseFloat(formData.coupon_rate || 0),
        lot_size: parseInt(formData.lot_size || 1),
        current_market_price: formData.current_market_price ? parseFloat(formData.current_market_price) : null,
        call_price: formData.call_price ? parseFloat(formData.call_price) : null,
        put_price: formData.put_price ? parseFloat(formData.put_price) : null,
      };

      if (editingInstrument) {
        await api.put(`/api/fixed-income/instruments/${editingInstrument.id}`, payload);
        toast.success('Instrument updated successfully');
      } else {
        await api.post('/fixed-income/instruments', payload);
        toast.success('Instrument created successfully');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchInstruments();
    } catch (error) {
      console.error('Error saving instrument:', error);
      toast.error(error.response?.data?.detail || 'Failed to save instrument');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate this instrument?')) return;
    
    try {
      await api.delete(`/api/fixed-income/instruments/${id}`);
      toast.success('Instrument deactivated');
      fetchInstruments();
    } catch (error) {
      toast.error('Failed to delete instrument');
    }
  };

  const handleCalculate = async () => {
    if (!calcData.isin || !calcData.clean_price) {
      toast.error('Please enter ISIN and Clean Price');
      return;
    }

    try {
      const response = await api.post('/fixed-income/instruments/calculate-pricing', null, {
        params: {
          isin: calcData.isin,
          clean_price: parseFloat(calcData.clean_price),
          settlement_date: calcData.settlement_date,
        }
      });
      setCalcResult(response.data);
      toast.success('Pricing calculated');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Calculation failed');
    }
  };

  const handlePriceFromYield = async () => {
    if (!calcData.isin || !calcData.target_ytm) {
      toast.error('Please enter ISIN and Target YTM');
      return;
    }

    try {
      const response = await api.post('/fixed-income/instruments/price-from-yield', null, {
        params: {
          isin: calcData.isin,
          target_ytm: parseFloat(calcData.target_ytm),
          settlement_date: calcData.settlement_date,
        }
      });
      setCalcResult(response.data);
      toast.success('Price calculated from yield');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Calculation failed');
    }
  };

  const resetForm = () => {
    setFormData({
      isin: '',
      instrument_type: 'NCD',
      issuer_name: '',
      issuer_code: '',
      face_value: '1000',
      issue_date: '',
      maturity_date: '',
      coupon_rate: '',
      coupon_frequency: 'annual',
      day_count_convention: 'ACT/365',
      credit_rating: 'UNRATED',
      rating_agency: '',
      current_market_price: '',
      is_callable: false,
      call_date: '',
      call_price: '',
      is_puttable: false,
      put_date: '',
      put_price: '',
      lot_size: '1',
    });
    setEditingInstrument(null);
  };

  const openEditDialog = (instrument) => {
    setEditingInstrument(instrument);
    setFormData({
      isin: instrument.isin || '',
      instrument_type: instrument.instrument_type || 'NCD',
      issuer_name: instrument.issuer_name || '',
      issuer_code: instrument.issuer_code || '',
      face_value: instrument.face_value?.toString() || '1000',
      issue_date: instrument.issue_date || '',
      maturity_date: instrument.maturity_date || '',
      coupon_rate: instrument.coupon_rate?.toString() || '',
      coupon_frequency: instrument.coupon_frequency || 'annual',
      day_count_convention: instrument.day_count_convention || 'ACT/365',
      credit_rating: instrument.credit_rating || 'UNRATED',
      rating_agency: instrument.rating_agency || '',
      current_market_price: instrument.current_market_price?.toString() || '',
      is_callable: instrument.is_callable || false,
      call_date: instrument.call_date || '',
      call_price: instrument.call_price?.toString() || '',
      is_puttable: instrument.is_puttable || false,
      put_date: instrument.put_date || '',
      put_price: instrument.put_price?.toString() || '',
      lot_size: instrument.lot_size?.toString() || '1',
    });
    setDialogOpen(true);
  };

  const viewInstrumentDetails = (instrument) => {
    setSelectedInstrument(instrument);
    setDetailDialogOpen(true);
  };

  const getRatingBadgeColor = (rating) => {
    if (!rating) return 'secondary';
    if (rating.startsWith('AAA')) return 'default';
    if (rating.startsWith('AA')) return 'default';
    if (rating.startsWith('A')) return 'secondary';
    if (rating.startsWith('BBB')) return 'outline';
    return 'destructive';
  };

  const filteredInstruments = instruments.filter(inst =>
    inst.issuer_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inst.isin?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inst.issuer_code?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="fi-security-master">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Building2 className="h-6 w-6 text-emerald-600" />
            Fixed Income - Security Master
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage NCDs, Bonds and other fixed income instruments
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setCalcDialogOpen(true)}
            data-testid="calc-btn"
          >
            <Calculator className="h-4 w-4 mr-2" />
            Calculator
          </Button>
          {isPELevel && (
            <>
              <Button
                variant="outline"
                onClick={() => setNsdlSearchOpen(true)}
                data-testid="nsdl-search-btn"
                className="border-blue-300 text-blue-700 hover:bg-blue-50"
              >
                <Search className="h-4 w-4 mr-2" />
                NSDL Search
              </Button>
              <Button
                variant="outline"
                onClick={handleImportPublicData}
                disabled={importingPublicData}
                data-testid="import-public-btn"
                className="border-teal-300 text-teal-700 hover:bg-teal-50"
              >
                <Download className={`h-4 w-4 mr-2 ${importingPublicData ? 'animate-spin' : ''}`} />
                {importingPublicData ? 'Importing...' : 'Import All'}
              </Button>
              <Button
                variant="outline"
                onClick={() => setBulkDialogOpen(true)}
                data-testid="bulk-upload-btn"
              >
                <Upload className="h-4 w-4 mr-2" />
                Bulk Upload
              </Button>
              <Button
                onClick={() => { resetForm(); setDialogOpen(true); }}
                className="bg-emerald-600 hover:bg-emerald-700"
                data-testid="add-instrument-btn"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Instrument
              </Button>
            </>
          )}
        </div>
      </div>

      {/* NSDL Search Dialog */}
      <Dialog open={nsdlSearchOpen} onOpenChange={setNsdlSearchOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Search className="h-5 w-5 text-blue-600" />
              Search NSDL Database
            </DialogTitle>
            <DialogDescription>
              Search for NCDs, Bonds, and G-Secs by ISIN or Company name and import them into Security Master
            </DialogDescription>
          </DialogHeader>
          
          {/* Search Form */}
          <div className="flex gap-2 mb-4">
            <Input 
              placeholder="Enter ISIN (e.g., INE002A) or Company name (e.g., Reliance, HDFC)..."
              value={nsdlSearchQuery}
              onChange={(e) => setNsdlSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleNsdlSearch()}
              className="flex-1"
              data-testid="nsdl-search-input"
            />
            <Select value={nsdlSearchType} onValueChange={setNsdlSearchType}>
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Fields</SelectItem>
                <SelectItem value="isin">ISIN Only</SelectItem>
                <SelectItem value="company">Company Only</SelectItem>
                <SelectItem value="rating">By Rating</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleNsdlSearch} disabled={nsdlSearching} className="bg-blue-600 hover:bg-blue-700">
              {nsdlSearching ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </>
              )}
            </Button>
          </div>

          {/* Search Results */}
          <div className="flex-1 overflow-y-auto">
            {nsdlSearchResults.length > 0 ? (
              <>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-muted-foreground">
                    Found {nsdlSearchResults.length} instruments
                    {nsdlSearchResults.filter(r => r.can_import).length > 0 && (
                      <span className="ml-2 text-green-600">
                        ({nsdlSearchResults.filter(r => r.can_import).length} available to import)
                      </span>
                    )}
                  </span>
                  {nsdlSearchResults.filter(r => r.can_import).length > 0 && (
                    <Button 
                      size="sm" 
                      variant="outline" 
                      onClick={handleNsdlImportAll}
                      className="border-green-300 text-green-700 hover:bg-green-50"
                    >
                      <Download className="h-3 w-3 mr-1" />
                      Import All Available
                    </Button>
                  )}
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ISIN</TableHead>
                      <TableHead>Issuer</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Coupon</TableHead>
                      <TableHead>Rating</TableHead>
                      <TableHead>Maturity</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {nsdlSearchResults.map((result) => (
                      <TableRow key={result.isin} className={result.already_imported ? 'bg-gray-50' : ''}>
                        <TableCell className="font-mono text-xs">{result.isin}</TableCell>
                        <TableCell className="max-w-[200px] truncate" title={result.issuer_name}>
                          {result.issuer_name}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {result.instrument_type}
                          </Badge>
                        </TableCell>
                        <TableCell>{result.coupon_rate}%</TableCell>
                        <TableCell>
                          <Badge className={
                            result.credit_rating === 'AAA' ? 'bg-green-100 text-green-800' :
                            result.credit_rating === 'SOVEREIGN' ? 'bg-orange-100 text-orange-800' :
                            result.credit_rating?.startsWith('AA') ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                          }>
                            {result.credit_rating}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs">{result.maturity_date}</TableCell>
                        <TableCell className="text-right">
                          {result.already_imported ? (
                            <Badge variant="outline" className="text-gray-500">
                              <Check className="h-3 w-3 mr-1" />
                              Imported
                            </Badge>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => handleNsdlImport(result.isin)}
                              disabled={nsdlImporting[result.isin]}
                              className="bg-green-600 hover:bg-green-700 h-7 text-xs"
                            >
                              {nsdlImporting[result.isin] ? (
                                <RefreshCw className="h-3 w-3 animate-spin" />
                              ) : (
                                <>
                                  <Download className="h-3 w-3 mr-1" />
                                  Import
                                </>
                              )}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Search className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p className="text-lg font-medium">Search NSDL Database</p>
                <p className="text-sm mt-1">Enter ISIN or company name to find NCDs, Bonds, and G-Secs</p>
                <div className="mt-4 text-xs text-gray-400">
                  <p>Examples: "INE002A", "Reliance", "HDFC", "Bajaj", "AAA"</p>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by ISIN, Issuer name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                data-testid="search-input"
              />
            </div>
            <Select value={filters.credit_rating || "all"} onValueChange={(v) => setFilters(prev => ({ ...prev, credit_rating: v === "all" ? "" : v }))}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Rating" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Ratings</SelectItem>
                {CREDIT_RATINGS.map(r => (
                  <SelectItem key={r} value={r}>{r}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={fetchInstruments}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="NCD">NCDs</TabsTrigger>
          <TabsTrigger value="BOND">Bonds</TabsTrigger>
          <TabsTrigger value="GSEC">G-Secs</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          <Card>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-6 space-y-4">
                  {[1,2,3,4,5].map(i => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : (
                <ScrollArea className="h-[600px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ISIN</TableHead>
                        <TableHead>Issuer</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Face Value</TableHead>
                        <TableHead className="text-right">Coupon</TableHead>
                        <TableHead>Maturity</TableHead>
                        <TableHead>Rating</TableHead>
                        <TableHead className="text-right">CMP</TableHead>
                        <TableHead className="text-right">YTM</TableHead>
                        <TableHead className="text-center">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredInstruments.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={10} className="text-center py-8 text-gray-500">
                            No instruments found
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredInstruments.map((inst) => (
                          <TableRow key={inst.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                            <TableCell className="font-mono text-xs">{inst.isin}</TableCell>
                            <TableCell>
                              <div className="max-w-[200px] truncate font-medium">
                                {inst.issuer_name}
                              </div>
                              {inst.issuer_code && (
                                <div className="text-xs text-gray-500">{inst.issuer_code}</div>
                              )}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{inst.instrument_type}</Badge>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              ₹{parseFloat(inst.face_value || 0).toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-1">
                                <Percent className="h-3 w-3 text-gray-400" />
                                {parseFloat(inst.coupon_rate || 0).toFixed(2)}
                              </div>
                              <div className="text-xs text-gray-500">
                                {inst.coupon_frequency?.replace('_', ' ')}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3 w-3 text-gray-400" />
                                {inst.maturity_date}
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant={getRatingBadgeColor(inst.credit_rating)}>
                                {inst.credit_rating || 'NR'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {inst.current_market_price ? 
                                `₹${parseFloat(inst.current_market_price).toFixed(2)}` : 
                                '-'
                              }
                            </TableCell>
                            <TableCell className="text-right">
                              {inst.ytm ? (
                                <span className="text-emerald-600 font-semibold">
                                  {parseFloat(inst.ytm).toFixed(2)}%
                                </span>
                              ) : '-'}
                            </TableCell>
                            <TableCell>
                              <div className="flex justify-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => viewInstrumentDetails(inst)}
                                  data-testid={`view-${inst.id}`}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                                {isPELevel && (
                                  <>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => openEditDialog(inst)}
                                      data-testid={`edit-${inst.id}`}
                                    >
                                      <Pencil className="h-4 w-4" />
                                    </Button>
                                    {isPEDesk && (
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleDelete(inst.id)}
                                        className="text-red-500 hover:text-red-700"
                                        data-testid={`delete-${inst.id}`}
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    )}
                                  </>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-gray-500">
              Showing {pagination.skip + 1} to {Math.min(pagination.skip + pagination.limit, pagination.total)} of {pagination.total}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={pagination.skip === 0}
                onClick={() => setPagination(prev => ({ ...prev, skip: prev.skip - prev.limit }))}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={pagination.skip + pagination.limit >= pagination.total}
                onClick={() => setPagination(prev => ({ ...prev, skip: prev.skip + prev.limit }))}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingInstrument ? 'Edit Instrument' : 'Add New Instrument'}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>ISIN *</Label>
                <Input
                  value={formData.isin}
                  onChange={(e) => setFormData(prev => ({ ...prev, isin: e.target.value.toUpperCase() }))}
                  placeholder="INE123A01234"
                  required
                  disabled={!!editingInstrument}
                />
              </div>
              <div>
                <Label>Instrument Type</Label>
                <Select value={formData.instrument_type} onValueChange={(v) => setFormData(prev => ({ ...prev, instrument_type: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {INSTRUMENT_TYPES.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Issuer Name *</Label>
                <Input
                  value={formData.issuer_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, issuer_name: e.target.value }))}
                  placeholder="Company Name"
                  required
                />
              </div>
              <div>
                <Label>Issuer Code</Label>
                <Input
                  value={formData.issuer_code}
                  onChange={(e) => setFormData(prev => ({ ...prev, issuer_code: e.target.value.toUpperCase() }))}
                  placeholder="ABC"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Face Value *</Label>
                <Input
                  type="number"
                  value={formData.face_value}
                  onChange={(e) => setFormData(prev => ({ ...prev, face_value: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label>Issue Date *</Label>
                <Input
                  type="date"
                  value={formData.issue_date}
                  onChange={(e) => setFormData(prev => ({ ...prev, issue_date: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label>Maturity Date *</Label>
                <Input
                  type="date"
                  value={formData.maturity_date}
                  onChange={(e) => setFormData(prev => ({ ...prev, maturity_date: e.target.value }))}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Coupon Rate (%) *</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.coupon_rate}
                  onChange={(e) => setFormData(prev => ({ ...prev, coupon_rate: e.target.value }))}
                  placeholder="8.50"
                  required
                />
              </div>
              <div>
                <Label>Coupon Frequency</Label>
                <Select value={formData.coupon_frequency} onValueChange={(v) => setFormData(prev => ({ ...prev, coupon_frequency: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COUPON_FREQUENCIES.map(f => (
                      <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Day Count Convention</Label>
                <Select value={formData.day_count_convention} onValueChange={(v) => setFormData(prev => ({ ...prev, day_count_convention: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DAY_COUNT_CONVENTIONS.map(d => (
                      <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Credit Rating</Label>
                <Select value={formData.credit_rating} onValueChange={(v) => setFormData(prev => ({ ...prev, credit_rating: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CREDIT_RATINGS.map(r => (
                      <SelectItem key={r} value={r}>{r}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Rating Agency</Label>
                <Input
                  value={formData.rating_agency}
                  onChange={(e) => setFormData(prev => ({ ...prev, rating_agency: e.target.value }))}
                  placeholder="CRISIL, ICRA, etc."
                />
              </div>
              <div>
                <Label>Current Market Price</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.current_market_price}
                  onChange={(e) => setFormData(prev => ({ ...prev, current_market_price: e.target.value }))}
                  placeholder="1050.00"
                />
              </div>
            </div>

            <div>
              <Label>Lot Size</Label>
              <Input
                type="number"
                value={formData.lot_size}
                onChange={(e) => setFormData(prev => ({ ...prev, lot_size: e.target.value }))}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700">
                {editingInstrument ? 'Update' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Calculator Dialog */}
      <Dialog open={calcDialogOpen} onOpenChange={setCalcDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5 text-emerald-600" />
              Bond Pricing Calculator
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>ISIN</Label>
              <Input
                value={calcData.isin}
                onChange={(e) => setCalcData(prev => ({ ...prev, isin: e.target.value.toUpperCase() }))}
                placeholder="INE123A01234"
              />
            </div>
            <div>
              <Label>Settlement Date</Label>
              <Input
                type="date"
                value={calcData.settlement_date}
                onChange={(e) => setCalcData(prev => ({ ...prev, settlement_date: e.target.value }))}
              />
            </div>
            
            <div className="border-t pt-4">
              <h4 className="font-medium mb-2">Calculate from Clean Price</h4>
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.01"
                  value={calcData.clean_price}
                  onChange={(e) => setCalcData(prev => ({ ...prev, clean_price: e.target.value }))}
                  placeholder="Clean Price"
                />
                <Button onClick={handleCalculate} className="bg-emerald-600 hover:bg-emerald-700">
                  Calculate YTM
                </Button>
              </div>
            </div>

            <div className="border-t pt-4">
              <h4 className="font-medium mb-2">Calculate Price from YTM</h4>
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.01"
                  value={calcData.target_ytm}
                  onChange={(e) => setCalcData(prev => ({ ...prev, target_ytm: e.target.value }))}
                  placeholder="Target YTM %"
                />
                <Button onClick={handlePriceFromYield} variant="outline">
                  Get Price
                </Button>
              </div>
            </div>

            {calcResult && (
              <Card className="bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200">
                <CardContent className="pt-4">
                  <h4 className="font-semibold text-emerald-700 dark:text-emerald-400 mb-2">Results</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>Clean Price:</div>
                    <div className="font-mono">₹{calcResult.clean_price}</div>
                    <div>Accrued Interest:</div>
                    <div className="font-mono">₹{calcResult.accrued_interest}</div>
                    <div>Dirty Price:</div>
                    <div className="font-mono font-semibold">₹{calcResult.dirty_price}</div>
                    {calcResult.ytm && (
                      <>
                        <div>YTM:</div>
                        <div className="font-mono text-emerald-600 font-semibold">{calcResult.ytm}%</div>
                      </>
                    )}
                    {calcResult.duration && (
                      <>
                        <div>Duration:</div>
                        <div className="font-mono">{calcResult.duration} years</div>
                      </>
                    )}
                    {calcResult.modified_duration && (
                      <>
                        <div>Modified Duration:</div>
                        <div className="font-mono">{calcResult.modified_duration}</div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Instrument Details</DialogTitle>
          </DialogHeader>
          
          {selectedInstrument && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-gray-500">Issuer</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="font-semibold">{selectedInstrument.issuer_name}</p>
                    <p className="text-sm text-gray-500">{selectedInstrument.isin}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-gray-500">Credit Rating</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Badge variant={getRatingBadgeColor(selectedInstrument.credit_rating)} className="text-lg">
                      {selectedInstrument.credit_rating || 'UNRATED'}
                    </Badge>
                    {selectedInstrument.rating_agency && (
                      <p className="text-sm text-gray-500 mt-1">{selectedInstrument.rating_agency}</p>
                    )}
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Face Value</p>
                      <p className="font-semibold">₹{parseFloat(selectedInstrument.face_value || 0).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Coupon Rate</p>
                      <p className="font-semibold">{selectedInstrument.coupon_rate}%</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Frequency</p>
                      <p className="font-semibold capitalize">{selectedInstrument.coupon_frequency?.replace('_', ' ')}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Day Count</p>
                      <p className="font-semibold">{selectedInstrument.day_count_convention}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Issue Date</p>
                      <p className="font-semibold">{selectedInstrument.issue_date}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Maturity Date</p>
                      <p className="font-semibold">{selectedInstrument.maturity_date}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Type</p>
                      <Badge>{selectedInstrument.instrument_type}</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {(selectedInstrument.current_market_price || selectedInstrument.ytm) && (
                <Card className="bg-emerald-50 dark:bg-emerald-900/20">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Current Market Data</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <p className="text-sm text-gray-500">CMP</p>
                        <p className="font-semibold text-lg">
                          {selectedInstrument.current_market_price ? `₹${selectedInstrument.current_market_price}` : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Accrued Int.</p>
                        <p className="font-semibold">
                          {selectedInstrument.accrued_interest ? `₹${selectedInstrument.accrued_interest}` : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Dirty Price</p>
                        <p className="font-semibold">
                          {selectedInstrument.dirty_price ? `₹${selectedInstrument.dirty_price}` : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">YTM</p>
                        <p className="font-semibold text-emerald-600 text-lg">
                          {selectedInstrument.ytm ? `${selectedInstrument.ytm}%` : '-'}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Bulk Upload Dialog */}
      <Dialog open={bulkDialogOpen} onOpenChange={setBulkDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5" />
              Bulk Upload Instruments
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Upload a CSV file with instrument data. Required columns: ISIN, Issuer Name, Face Value, Issue Date, Maturity Date, Coupon Rate.
            </p>
            <Button variant="outline" className="w-full">
              <Download className="h-4 w-4 mr-2" />
              Download Template
            </Button>
            <Input type="file" accept=".csv,.xlsx" />
            <DialogFooter>
              <Button variant="outline" onClick={() => setBulkDialogOpen(false)}>Cancel</Button>
              <Button className="bg-emerald-600 hover:bg-emerald-700">Upload</Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FISecurityMaster;
