
import Sidebar from '../components/Sidebar';
import SearchBar from '../components/SearchBar';
import CandlestickChart from '../components/CandlestickChart';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom'

const Index = () => {
  return (
    <div className="flex h-screen w-full bg-white overflow-hidden">
      <Sidebar />
      
      <div className="flex-1 overflow-auto">
        <header className="p-4 flex justify-between items-center">
          <SearchBar />
          {/* <Button className="bg-neuro-blue hover:bg-blue-700 text-white px-6">
            BUILD YOUR INVESTING MODEL
          </Button> */}
          <Link to="/workflow">
  <Button className="bg-neuro-blue hover:bg-blue-700 text-white px-6">
    BUILD YOUR INVESTING MODEL
  </Button>
</Link>
        </header>
        
        <main className="px-4 pb-8">
          {/* Hero Section */}
          <section className="mb-6">
            <div className="rounded-lg overflow-hidden bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-12">
              <h2 className="text-3xl md:text-4xl font-bold mb-2">Build Your Own Ai Model to Invest in Web3</h2>
              <p className="text-2xl md:text-3xl text-blue-100">or invest in PreBuild Growing Models</p>
            </div>
          </section>
          
          {/* Charts Section */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CandlestickChart 
              title="Dev's FinSrtument" 
              percentage="92%" 
              className="md:col-span-2"
            />
            
            <div className="bg-gray-100 p-6 rounded-lg flex flex-col">
              <div className="flex-1">
                <CandlestickChart 
                  title="" 
                  className="bg-transparent shadow-none p-0"
                />
              </div>
              <Button className="w-full mt-4 bg-gray-200 text-gray-700 hover:bg-gray-300">
                Invest in any Person's Instrument
              </Button>
            </div>
          </section>
          
          {/* Performance Metrics Section */}
          <section className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {['Daily Performance', 'Weekly Growth', 'Monthly Return', 'Yearly Forecast'].map((title, index) => (
              <div key={index} className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                <h3 className="text-sm font-medium text-gray-500">{title}</h3>
                <p className="text-2xl font-bold mt-1">{(Math.random() * 10).toFixed(2)}%</p>
                <div className="h-[80px] mt-2">
                  <ResponsiveChartPlaceholder positive={index % 2 === 0} />
                </div>
              </div>
            ))}
          </section>
          
          {/* Recent Transactions */}
          <section className="mt-8">
            <h2 className="text-xl font-bold mb-4">Recent Transactions</h2>
            <div className="bg-white rounded-lg shadow-sm overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {[1, 2, 3, 4, 5].map((item) => (
                    <tr key={item} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">EthModel #{item}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item % 2 === 0 ? 'Buy' : 'Sell'}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${(Math.random() * 1000).toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">2025-04-{10 + item}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          item % 3 === 0 ? 'bg-yellow-100 text-yellow-800' : 
                          item % 3 === 1 ? 'bg-green-100 text-green-800' : 
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {item % 3 === 0 ? 'Pending' : item % 3 === 1 ? 'Completed' : 'Processing'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};

// Simple visual component for small charts in metrics cards
const ResponsiveChartPlaceholder = ({ positive }: { positive: boolean }) => {
  const color = positive ? '#4ade80' : '#f87171';
  
  return (
    <svg className="w-full h-full" viewBox="0 0 100 30">
      <path 
        d={positive ? 
          'M0,20 L10,15 L20,18 L30,10 L40,12 L50,5 L60,8 L70,3 L80,6 L90,2 L100,5' : 
          'M0,5 L10,8 L20,6 L30,12 L40,10 L50,15 L60,13 L70,18 L80,15 L90,20 L100,17'} 
        fill="none" 
        stroke={color} 
        strokeWidth="2" 
      />
      <path 
        d={positive ? 
          'M0,20 L10,15 L20,18 L30,10 L40,12 L50,5 L60,8 L70,3 L80,6 L90,2 L100,5 L100,30 L0,30 Z' : 
          'M0,5 L10,8 L20,6 L30,12 L40,10 L50,15 L60,13 L70,18 L80,15 L90,20 L100,17 L100,30 L0,30 Z'} 
        fill={`${color}20`}
      />
    </svg>
  );
};

export default Index;
