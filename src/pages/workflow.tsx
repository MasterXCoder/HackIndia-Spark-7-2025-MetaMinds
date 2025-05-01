import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, Calculator, ImageIcon, MessageSquare, LayoutList, Smartphone, Terminal } from "lucide-react";
import { motion } from "framer-motion";
import {
  ReactFlowProvider,
  ReactFlow,
  addEdge,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
} from "reactflow";
import "reactflow/dist/style.css";

const AssetSelector = () => {
  return (
    <div className="space-y-2">
      <label className="block font-medium">Choose Investment Asset:</label>
      <select className="p-2 border rounded w-full">
        <option value="bitcoin">Bitcoin</option>
        <option value="ethereum">Ethereum</option>
        <option value="sohana">Solana</option>
      </select>
      <Button className="mt-2 bg-blue-600 hover:bg-blue-700 text-white w-full">Confirm Asset</Button>
    </div>
  );
};

const Toolbar = ({ onCalculatorClick }) => {
  return (
    <div className="flex items-center justify-center space-x-6 bg-gray-200 px-6 py-2 rounded-xl shadow">
      <ArrowRight className="cursor-pointer" />
      <ImageIcon className="cursor-pointer" />
      <MessageSquare className="cursor-pointer" />
      <LayoutList className="cursor-pointer" />
      <Calculator className="cursor-pointer" onClick={onCalculatorClick} />
      <Smartphone className="cursor-pointer" />
      <Terminal className="cursor-pointer" />
      <span className="font-bold">&</span>
      <span className="font-bold">OR</span>
    </div>
  );
};

const initialNodes:any = [
  {
    id: "1",
    type: "input",
    data: { label: <AssetSelector /> },
    position: { x: 50, y: 50 },
  },
  {
    id: "2",
    data: {
      label: <img src="/images/chart1.png" alt="Chart 1" className="rounded-xl w-32" />,
    },
    position: { x: 250, y: 50 },
  },
  {
    id: "3",
    data: {
      label: (
        <div className="p-2">
          If the price of Bitcoin decreases as shown, initiate a 3% investment automatically.
        </div>
      ),
    },
    position: { x: 450, y: 50 },
  },
  {
    id: "4",
    type: "output",
    data: { label: "Invest" },
    position: { x: 700, y: 50 },
  },
];

const initialEdges = [
  { id: "e1-2", source: "1", target: "2", animated: true },
  { id: "e2-3", source: "2", target: "3", animated: true },
  { id: "e3-4", source: "3", target: "4", animated: true },
];

const FlowCanvas = ({ nodes, setNodes, edges, setEdges, onNodesChange, onEdgesChange }) => {
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={(params) => setEdges((eds) => addEdge(params, eds))}
      fitView
    >
      <MiniMap />
      <Controls />
      <Background gap={12} size={1} />
    </ReactFlow>
  );
};

const Dashboard = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const handleCalculatorClick = () => {
    const newNodeId = (nodes.length + 1).toString();
    const newNode = {
      id: newNodeId,
      data: {
        label: (
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Enter calculation (e.g. myholdings/2)"
              onChange={(e) => {
                const input = e.target.value;
                const resultDiv = e.target.nextSibling;
                try {
                  const variableMap = {
                    myholdings: 5000,
                    currentbalance: 2000,
                  };
                  const expression = input.replace(/\b[a-zA-Z]+\b/g, (match) => {
                    if (variableMap.hasOwnProperty(match)) {
                      return variableMap[match];
                    }
                    throw new Error(`Unknown variable: ${match}`);
                  });
                  const result = Function(`"use strict"; return (${expression})`)();
                  resultDiv.textContent = `Result: ${result}`;
                } catch {
                  resultDiv.textContent = "Result: Error";
                }
              }}
              className="p-2 border rounded w-full"
            />
            <div className="text-sm font-medium">Result: </div>
          </div>
        ),
      },
      position: { x: 100 + nodes.length * 50, y: 300 },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6 space-y-4">
      <h1 className="text-3xl font-bold text-center mb-10 mt-8">NeuroTrader</h1>
      {/* <Toolbar onCalculatorClick={handleCalculatorClick} /> */}

      <ReactFlowProvider>
        <div style={{ width: "100%", height: 500 }} className="bg-white rounded-xl shadow-md">
          <FlowCanvas
            nodes={nodes}
            setNodes={setNodes}
            edges={edges}
            setEdges={setEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
          />
        </div>
      </ReactFlowProvider>

      <Toolbar onCalculatorClick={handleCalculatorClick} />
    </div>
  );
};

export default Dashboard;
