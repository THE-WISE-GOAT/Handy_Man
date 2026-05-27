import React, { useState } from 'react';
import { Search, MapPin, Tag, Users, Shield, Sliders, Calendar, Star, ChevronRight } from 'lucide-react';

const HomePage = () => {
  // --- STATE FOR FILTER & SEARCH ---
  const [location, setLocation] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [hiringTier, setHiringTier] = useState('single'); // single, multiple, agency
  const [radius, setRadius] = useState(10); // in km or miles

  // --- HANDLER FOR SEARCH ---
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    console.log('Searching with params:', { location, selectedTag, hiringTier, radius });
    
    /**
     * BACKEND INTEGRATION POINT:
     * 1. Send an HTTP GET or POST request to your Python/FastAPI endpoint.
     * e.g., fetch(`http://localhost:8000/api/jobs/match?lat=...&lng=...&tag=${selectedTag}&tier=${hiringTier}`)
     * 2. Handle the geospatial matching list returned from PostGIS.
     * 3. Redirect the user to the search results dashboard or populate a results grid below.
     */
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans antialiased">
      
      {/* 1. TOP NAVIGATION BAR */}
      <nav className="sticky top-0 z-50 bg-slate-900 text-white border-b border-slate-800 backdrop-blur-md bg-opacity-95 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2 cursor-pointer">
          <div className="h-8 w-8 bg-orange-500 rounded flex items-center justify-center font-bold text-lg">C</div>
          <span className="text-xl font-bold tracking-tight">ConnectWorkers</span>
        </div>
        
        <div className="hidden md:flex space-x-8 text-sm font-medium text-slate-300">
          <a href="#how-it-works" className="hover:text-orange-400 transition">How It Works</a>
          <a href="#find-worker" className="hover:text-orange-400 transition">Find a Worker</a>
          <a href="#become-worker" className="hover:text-orange-400 transition">Become a Worker</a>
        </div>

        <div className="flex items-center space-x-4">
          <button className="text-sm font-medium text-slate-300 hover:text-white transition">Login</button>
          <button className="bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold px-4 py-2 rounded-lg shadow-md transition transform active:scale-95">
            Post a Job
          </button>
        </div>
      </nav>

      {/* 2. HERO SECTION WITH COMPREHENSIVE SEARCH FILTER */}
      <header className="bg-gradient-to-b from-slate-900 to-slate-850 text-white px-6 py-20 text-center relative overflow-hidden">
        <div className="max-w-4xl mx-auto relative z-10">
          <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-4 leading-tight">
            Find Skilled Local Help, <span className="text-orange-500">Your Way.</span>
          </h1>
          <p className="text-lg text-slate-300 max-w-2xl mx-auto mb-8">
            Post your job, visually draw your dynamic service zone, and get matched with verified workers, independent groups, or professional agencies.
          </p>

          {/* DYNAMIC SEARCH BAR BAR */}
          <form onSubmit={handleSearchSubmit} className="bg-white text-slate-900 p-3 rounded-xl shadow-2xl flex flex-col lg:flex-row items-center gap-3 border border-slate-200">
            
            {/* Location Input */}
            <div className="w-full lg:w-1/3 flex items-center px-3 py-2 border-b lg:border-b-0 lg:border-r border-slate-200">
              <MapPin className="text-slate-400 mr-2 flex-shrink-0" size={20} />
              <input 
                type="text" 
                placeholder="Enter Zip Code / City Location" 
                className="w-full bg-transparent focus:outline-none text-sm font-medium"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                required
              />
            </div>

            {/* Tags / Skills Field */}
            <div className="w-full lg:w-1/3 flex items-center px-3 py-2 border-b lg:border-b-0 lg:border-r border-slate-200">
              <Tag className="text-slate-400 mr-2 flex-shrink-0" size={20} />
              <select 
                className="w-full bg-transparent focus:outline-none text-sm font-medium text-slate-600"
                value={selectedTag}
                onChange={(e) => setSelectedTag(e.target.value)}
                required
              >
                <option value="" disabled>Select #Tags (e.g., Plumbing)</option>
                <option value="plumbing">#Plumbing</option>
                <option value="electrical">#Electrical</option>
                <option value="painting">#Painting</option>
                <option value="barber">#At-Home Barber</option>
                <option value="mechanic">#Mechanics Service</option>
              </select>
            </div>

            {/* Hiring Tier Dropdown */}
            <div className="w-full lg:w-1/4 flex items-center px-3 py-2">
              <Users className="text-slate-400 mr-2 flex-shrink-0" size={20} />
              <select 
                className="w-full bg-transparent focus:outline-none text-sm font-medium text-slate-600"
                value={hiringTier}
                onChange={(e) => setHiringTier(e.target.value)}
              >
                <option value="single">Single Worker</option>
                <option value="multiple">Group Multiple Workers</option>
                <option value="agency">Professional Agency</option>
              </select>
            </div>

            {/* Submit Action */}
            <button type="submit" className="w-full lg:w-auto bg-orange-500 hover:bg-orange-600 text-white font-bold px-6 py-3 rounded-lg text-sm transition flex items-center justify-center space-x-2 shadow-lg flex-shrink-0">
              <Search size={18} />
              <span>Find Workers</span>
            </button>
          </form>
        </div>
        
        {/* Abstract Background Accents */}
        <div className="absolute top-0 left-0 right-0 bottom-0 opacity-10 pointer-events-none">
          <div className="absolute -top-20 -left-20 w-80 h-80 rounded-full bg-orange-500 filter blur-3xl"></div>
          <div className="absolute -bottom-20 -right-20 w-80 h-80 rounded-full bg-blue-500 filter blur-3xl"></div>
        </div>
      </header>

      {/* 3. MAIN WORKSPACE / MAIN LAYOUT DASHBOARD */}
      <main className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* LEFT & CENTER PARTS: CONTENT CORNER */}
        <div className="lg:col-span-2 space-y-12">
          
          {/* POPULAR CATEGORIES */}
          <section>
            <h2 className="text-2xl font-bold tracking-tight mb-6">Popular Services Near You</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { name: 'Plumbing', count: '14 Available', icon: '🔧' },
                { name: 'Handyman/Electrical', count: '29 Available', icon: '⚡' },
                { name: 'Barber At Home', count: '8 Available', icon: '💈' }
              ].map((category, idx) => (
                <div key={idx} className="bg-white p-5 rounded-xl border border-slate-200 hover:border-orange-300 shadow-sm hover:shadow-md transition cursor-pointer flex items-center space-x-4">
                  <div className="text-3xl">{category.icon}</div>
                  <div>
                    <h3 className="font-bold text-slate-900">{category.name}</h3>
                    <p className="text-xs text-slate-500">{category.count}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* DYNAMIC MULTI-TIER PREVIEW CASE PROJECTS */}
          <section>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold tracking-tight">Flexible Hiring Tiers</h2>
              <span className="text-xs bg-slate-200 text-slate-700 px-3 py-1 rounded-full font-semibold">Scale System Demo</span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Scenario 1: Group Multiple Independent Workers */}
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition">
                <div className="h-44 bg-slate-200 flex items-center justify-center text-slate-400 relative">
                  <span className="text-sm font-mono">[Illustration: House Painting Grouping]</span>
                  <div className="absolute top-3 left-3 bg-blue-600 text-white text-xs px-2 py-1 rounded font-bold">
                    Modular: Group Hiring
                  </div>
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-lg mb-2">Entire House Painting Project</h3>
                  <p className="text-sm text-slate-600 mb-4">
                    Need a whole building colored? Bundle multiple local painters into a modular ecosystem. Discuss materials on meetup; no structural alignment rules necessary.
                  </p>
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                    <span>Est: Negotiation Model</span>
                    <span className="text-blue-600 flex items-center">Configure Group <ChevronRight size={14} /></span>
                  </div>
                </div>
              </div>

              {/* Scenario 2: Call Professional Shop/Agency */}
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition">
                <div className="h-44 bg-slate-200 flex items-center justify-center text-slate-400 relative">
                  <span className="text-sm font-mono">[Illustration: Blueprint Plumbing Agency]</span>
                  <div className="absolute top-3 left-3 bg-purple-600 text-white text-xs px-2 py-1 rounded font-bold">
                    Complex: Agency Assignment
                  </div>
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-lg mb-2">Full Plumbing Overhaul</h3>
                  <p className="text-sm text-slate-600 mb-4">
                    For tasks requiring strict coordination blueprints and deep structural liability, hire established architectural shops who manage their internal crews directly.
                  </p>
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                    <span>Est: Binding Contracts</span>
                    <span className="text-purple-600 flex items-center">View Top Agencies <ChevronRight size={14} /></span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* RIGHT PART: CONTROL PANEL & GEOSPATIAL MAP PLUG PANEL */}
        <aside className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6 h-fit">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <h3 className="font-bold text-lg flex items-center text-slate-900">
              <Sliders className="text-orange-500 mr-2" size={18} />
              Geospatial Controls
            </h3>
            <span className="text-xs font-mono text-slate-400">Worker View Map</span>
          </div>

          {/* RADIUS CONFIGURATION SLIDER */}
          <div>
            <div className="flex justify-between text-sm font-semibold mb-2">
              <label className="text-slate-700">Custom Service Zone</label>
              <span className="text-orange-500 font-mono">{radius} km radius</span>
            </div>
            <input 
              type="range" 
              min="1" 
              max="100" 
              value={radius} 
              onChange={(e) => setRadius(Number(e.target.value))}
              className="w-full accent-orange-500 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* SIMULATED MINIMALIST TIMELINE / CALENDAR PICKER TRACKER */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center">
              <Calendar size={16} className="mr-1.5 text-slate-400" />
              Availability Timeline Track
            </label>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-center">
              <span className="text-xs text-slate-500 block font-medium">Simple Conflict Scheduler Integration</span>
              <div className="mt-2 grid grid-cols-5 gap-1 text-center text-xs font-mono font-bold">
                <span className="bg-green-100 text-green-700 p-1.5 rounded">Mon</span>
                <span className="bg-green-100 text-green-700 p-1.5 rounded">Tue</span>
                <span className="bg-orange-100 text-orange-700 p-1.5 rounded">Wed</span>
                <span className="bg-green-100 text-green-700 p-1.5 rounded">Thu</span>
                <span className="bg-slate-100 text-slate-400 p-1.5 rounded">Fri</span>
              </div>
            </div>
          </div>

          {/* DYNAMIC MAP placeholder MODULE */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-slate-700">Live Geospatial Sandbox</label>
            <div className="bg-slate-100 h-56 rounded-xl border border-slate-300 relative flex flex-center items-center justify-center overflow-hidden">
              
              {/* BACKEND & UI MAP PLUG PLACEMENT INDICATION:
                -------------------------------------------------
                Replace this placeholder container div with an interactive mapping suite:
                e.g., <MapContainer>, <MapGL>, Leaflet, or Mapbox API instances.
                
                You will pass coordinates down to render:
                1. Central red locator dot marking the worker profile or requested task point.
                2. Vector circle component utilizing the `radius` state variable to define bounds.
              */}
              
              <div className="absolute inset-0 bg-slate-200 opacity-60 bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] [background-size:16px_16px]"></div>
              
              {/* Simulated Map Markers */}
              <div className="absolute w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow animate-pulse top-1/2 left-1/2 -mt-2 -ml-2 z-10"></div>
              <div className="absolute w-24 h-24 bg-red-400 bg-opacity-20 rounded-full border border-red-500 top-1/2 left-1/2 -mt-12 -ml-12"></div>
              <div className="absolute w-3 h-3 bg-orange-500 rounded-full border border-white shadow top-1/3 left-1/4"></div>
              <div className="absolute w-3 h-3 bg-blue-500 rounded-full border border-white shadow bottom-1/4 right-1/3"></div>

              <div className="absolute bottom-2 left-2 right-2 bg-white bg-opacity-90 backdrop-blur-sm p-2 rounded text-[10px] font-mono text-slate-600 shadow-sm border border-slate-200">
                Lat/Lng Query: Dynamic Real-time Overlay
              </div>
            </div>
          </div>

          {/* SYSTEM VERIFICATION TRUST BADGE */}
          <div className="bg-orange-50 rounded-xl p-4 border border-orange-100 flex items-start space-x-3">
            <Shield className="text-orange-500 mt-0.5 flex-shrink-0" size={18} />
            <div>
              <h4 className="text-xs font-bold text-orange-900 uppercase tracking-wider">Validation Safeguard</h4>
              <p className="text-xs text-orange-700 mt-0.5 leading-relaxed">
                Initial alpha release. Legal licensing checks & background authentication processes are evaluated via offline peer-reviewed rating loops.
              </p>
            </div>
          </div>
        </aside>

      </main>

      {/* 4. SEAMLESS CLEAN FOOTER FRAME */}
      <footer className="bg-slate-900 text-slate-400 px-6 py-12 mt-20 border-t border-slate-800 text-sm">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <h5 className="text-white font-bold mb-3">Company</h5>
            <ul className="space-y-2 text-xs">
              <li className="hover:text-white cursor-pointer transition">About Project Platform</li>
              <li className="hover:text-white cursor-pointer transition">Open Marketplace Hub</li>
            </ul>
          </div>
          <div>
            <h5 className="text-white font-bold mb-3">Support</h5>
            <ul className="space-y-2 text-xs">
              <li className="hover:text-white cursor-pointer transition">Client Negotiation Guides</li>
              <li className="hover:text-white cursor-pointer transition">Worker Zone Setup Help</li>
            </ul>
          </div>
          <div>
            <h5 className="text-white font-bold mb-3">Legal & Validation</h5>
            <ul className="space-y-2 text-xs">
              <li className="hover:text-white cursor-pointer transition">Terms & Working Conditions</li>
              <li className="hover:text-white cursor-pointer transition">Certification Policy Escrow</li>
            </ul>
          </div>
          <div>
            <h5 className="text-white font-bold mb-3">Social / Project Meta</h5>
            <p className="text-xs text-slate-500 leading-normal">
              Designed as a location-centric hybrid marketplace prototype utilizing a Python/FastAPI ecosystem backend.
            </p>
          </div>
        </div>
        <div className="max-w-7xl mx-auto mt-12 pt-6 border-t border-slate-800 text-center text-xs text-slate-500">
          &copy; {new Date().getFullYear()} ConnectWorkers Project Proposal Sandbox. All rights reserved.
        </div>
      </footer>

    </div>
  );
};

export default HomePage;