import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api/client';
import {
    useReactTable,
    getCoreRowModel,
    flexRender,
    getSortedRowModel,
} from '@tanstack/react-table';
import { ArrowUpDown, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function Reconciliation() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getReconciliationResults({ page: 1, limit: 100 })
            .then(res => setData(res.results))
            .finally(() => setLoading(false));
    }, []);

    const columns = useMemo(
        () => [
            {
                accessorKey: 'invoice_number',
                header: 'Invoice No.',
                cell: info => <span className="font-mono text-blue-600">{info.getValue()}</span>
            },
            {
                accessorKey: 'supplier_gstin',
                header: 'Supplier GSTIN',
            },
            {
                accessorKey: 'match_status',
                header: 'Status',
                cell: info => {
                    const val = info.getValue() || 'UNKNOWN';
                    const isMatch = val === 'FULL_MATCH';
                    return (
                        <span className={`px-3 py-1 text-xs font-semibold rounded-full ${isMatch ? 'bg-green-100 text-green-800' :
                                val.includes('MISMATCH') ? 'bg-orange-100 text-orange-800' :
                                    'bg-red-100 text-red-800'
                            }`}>
                            {val.replace(/_/g, ' ')}
                        </span>
                    );
                },
            },
            {
                id: 'gstr1_val',
                header: 'GSTR-1 Taxable',
                accessorFn: row => row.taxable_value_by_source?.GSTR1,
                cell: info => {
                    const val = info.getValue();
                    return val ? `₹${val.toLocaleString()}` : '-';
                }
            },
            {
                id: 'gstr2b_val',
                header: 'GSTR-2B Taxable',
                accessorFn: row => row.taxable_value_by_source?.GSTR2B,
                cell: info => {
                    const val = info.getValue();
                    return val ? `₹${val.toLocaleString()}` : '-';
                }
            },
            {
                accessorKey: 'itc_eligible',
                header: 'ITC',
                cell: info => info.getValue() ?
                    <CheckCircle2 className="w-5 h-5 text-green-500" /> :
                    <AlertCircle className="w-5 h-5 text-red-500" />
            }
        ],
        []
    );

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
    });

    if (loading) return <div className="p-8 text-center">Loading Reconciliation Data...</div>;

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-gray-900">Reconciliation Explorer</h1>
                <div className="flex space-x-2">
                    <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-md text-sm border font-medium">All Sources</span>
                    <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-md text-sm border font-medium">Mismatches Only</span>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-700">
                        <thead className="bg-gray-50 text-gray-600 uppercase font-semibold border-b">
                            {table.getHeaderGroups().map(headerGroup => (
                                <tr key={headerGroup.id}>
                                    {headerGroup.headers.map(header => (
                                        <th key={header.id} className="px-6 py-4 cursor-pointer hover:bg-gray-100" onClick={header.column.getToggleSortingHandler()}>
                                            <div className="flex items-center space-x-1">
                                                <span>{flexRender(header.column.columnDef.header, header.getContext())}</span>
                                                {header.column.getCanSort() && <ArrowUpDown className="w-4 h-4 text-gray-400" />}
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                            ))}
                        </thead>
                        <tbody>
                            {table.getRowModel().rows.map(row => (
                                <tr key={row.id} className="border-b hover:bg-gray-50 transition-colors">
                                    {row.getVisibleCells().map(cell => (
                                        <td key={cell.id} className="px-6 py-4">
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
