
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Mock data for the chart
const data = [
  { name: '1 Jan', value: 4000 },
  { name: '2 Jan', value: 3000 },
  { name: '3 Jan', value: 5000 },
  { name: '4 Jan', value: 2780 },
  { name: '5 Jan', value: 1890 },
  { name: '6 Jan', value: 2390 },
  { name: '7 Jan', value: 3490 },
  { name: '8 Jan', value: 3490 },
  { name: '9 Jan', value: 4000 },
  { name: '10 Jan', value: 5000 },
  { name: '11 Jan', value: 3500 },
  { name: '12 Jan', value: 4500 },
];

interface CandlestickChartProps {
  title: string;
  percentage?: string;
  className?: string;
}

const CandlestickChart = ({ title, percentage, className = "" }: CandlestickChartProps) => {
  return (
    <div className={`bg-white p-4 rounded-lg shadow-sm ${className}`}>
      <div className="flex justify-between items-start">
        <h3 className="text-xl font-bold">{title}</h3>
        {percentage && (
          <div className="text-4xl font-bold">{percentage}</div>
        )}
      </div>
      <div className="h-[200px] mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{
              top: 5,
              right: 0,
              left: 0,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Tooltip />
            <Area type="monotone" dataKey="value" stroke="#4361ee" fill="#4361ee20" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default CandlestickChart;
