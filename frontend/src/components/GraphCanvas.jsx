import React, { useRef, useEffect } from 'react';
import cytoscape from 'cytoscape';

export const GRAPH_STYLES = [
    {
        selector: 'node',
        style: {
            'label': 'data(legal_name)', // Fallback configured in mapper
            'font-size': '8px',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': '4px',
            'color': '#475569',
            'text-outline-width': 1,
            'text-outline-color': '#ffffff'
        }
    },
    {
        selector: 'node[_label = "Taxpayer"]',
        style: {
            'background-color': '#3B82F6',
            'shape': 'round-rectangle',
            'width': 60,
            'height': 30,
            'label': 'data(gstin)'
        }
    },
    {
        selector: 'node[_label = "Invoice"]',
        style: {
            'background-color': '#6366F1',
            'shape': 'ellipse',
            'width': 40,
            'height': 40,
            'label': 'data(invoice_number)'
        }
    },
    {
        selector: 'node[_label = "Return"]',
        style: {
            'background-color': '#8B5CF6',
            'shape': 'diamond',
            'width': 45,
            'height': 45,
            'label': 'data(return_type)'
        }
    },
    {
        selector: 'node[_label = "SourceObservation"]',
        style: {
            'background-color': '#94A3B8',
            'shape': 'ellipse',
            'width': 25,
            'height': 25,
            'label': 'data(source_system)'
        }
    },
    {
        selector: 'edge',
        style: {
            'width': 2,
            'line-color': '#CBD5E1',
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#CBD5E1',
            'font-size': '6px',
            'text-rotation': 'autorotate',
            'label': 'data(_type)',
            'color': '#94A3B8',
            'text-margin-y': -5
        }
    },
    {
        selector: 'edge[_type = "ISSUED_BY"]',
        style: { 'line-color': '#3B82F6', 'target-arrow-color': '#3B82F6' }
    },
    {
        selector: 'edge[_type = "RECEIVED_BY"]',
        style: { 'line-color': '#10B981', 'target-arrow-color': '#10B981' }
    },
    {
        selector: 'edge[_type = "REPORTED_IN"]',
        style: { 'line-color': '#8B5CF6', 'target-arrow-color': '#8B5CF6', 'line-style': 'dashed' }
    },
    {
        selector: 'edge[_type = "HAS_OBSERVATION"]',
        style: { 'line-color': '#94A3B8', 'target-arrow-color': '#94A3B8', 'line-style': 'dotted' }
    }
];

export default function GraphCanvas({ elements }) {
    const containerRef = useRef(null);
    const cyRef = useRef(null);

    useEffect(() => {
        if (!containerRef.current || !elements || elements.length === 0) return;

        // Destroy old if exists
        if (cyRef.current) {
            cyRef.current.destroy();
        }

        const cy = cytoscape({
            container: containerRef.current,
            elements: elements,
            style: GRAPH_STYLES,
            layout: {
                name: 'cose',
                padding: 50,
                nodeRepulsion: 400000,
                idealEdgeLength: 100,
                edgeElasticity: 100,
                gravity: 250,
                animate: true
            },
            wheelSensitivity: 0.2
        });

        cy.on('tap', 'node', function (evt) {
            var node = evt.target;
            console.log('Tapped ' + node.id());
        });

        cyRef.current = cy;

        return () => {
            if (cyRef.current) cyRef.current.destroy();
        };
    }, [elements]);

    return <div ref={containerRef} className="w-full h-full bg-gray-50" />;
}
