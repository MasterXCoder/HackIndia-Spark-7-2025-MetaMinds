
import { useState } from 'react';
import { ChevronDown, Settings } from 'lucide-react';

const Sidebar = () => {
  const [isModelsExpanded, setIsModelsExpanded] = useState(true);

  return (
    <div className="h-screen bg-neuro-lightgray w-[180px] flex-shrink-0 border-r border-gray-200">
      <div className="p-4">
        <h1 className="text-xl font-bold text-neuro-darkgray">NeuroTrader</h1>
      </div>

      <nav className="mt-6">
        <ul>
          <li className="px-4 py-2 hover:bg-gray-200 cursor-pointer">Home</li>
          <li className="px-4 py-2 hover:bg-gray-200 cursor-pointer">Trending</li>
          <li className="px-4 py-2 hover:bg-gray-200 cursor-pointer">Resources</li>
          <li className="px-4 py-2 hover:bg-gray-200 cursor-pointer">How it Works</li>
        </ul>

        <div className="mt-6 border-t border-gray-300 pt-4">
          <div 
            className="px-4 py-2 flex items-center justify-between cursor-pointer"
            onClick={() => setIsModelsExpanded(!isModelsExpanded)}
          >
            <h2 className="font-bold">My Models</h2>
            <ChevronDown 
              size={18} 
              className={`transition-transform ${isModelsExpanded ? 'transform rotate-180' : ''}`}
            />
          </div>
          
          {isModelsExpanded && (
            <ul className="mt-2">
              <li className="px-6 py-2 hover:bg-gray-200 cursor-pointer">My EthModel</li>
              <li className="px-6 py-2 hover:bg-gray-200 cursor-pointer">Pooling Model</li>
            </ul>
          )}
        </div>
      </nav>

      <div className="absolute bottom-4 px-4 py-2 flex items-center cursor-pointer">
        <Settings size={18} className="mr-2" />
        <span>Settings</span>
      </div>
    </div>
  );
};

export default Sidebar;
