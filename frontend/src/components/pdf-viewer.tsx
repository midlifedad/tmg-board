"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  FileText,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

interface PdfViewerProps {
  url: string;
  title?: string;
  userEmail?: string;
}

export function PdfViewer({ url, title, userEmail }: PdfViewerProps) {
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const fullscreenRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!userEmail) return;
    let cancelled = false;
    setLoadError(null);
    setPdfData(null);
    async function fetchPdf() {
      try {
        const response = await fetch(url, {
          headers: { "X-User-Email": userEmail! },
        });
        if (!response.ok) {
          throw new Error(`Failed to load PDF (${response.status})`);
        }
        const buffer = await response.arrayBuffer();
        if (!cancelled) {
          setPdfData(buffer);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Failed to load PDF");
        }
      }
    }
    fetchPdf();
    return () => { cancelled = true; };
  }, [url, userEmail]);

  const onDocumentLoadSuccess = useCallback(
    ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      setPageNumber(1);
      setLoadError(null);
    },
    []
  );

  const onDocumentLoadError = useCallback((error: Error) => {
    setLoadError(error.message || "Failed to load PDF");
  }, []);

  const goToPrevPage = () => setPageNumber((p) => Math.max(1, p - 1));
  const goToNextPage = () => setPageNumber((p) => Math.min(numPages, p + 1));
  const zoomIn = () => setScale((s) => Math.min(3, s + 0.25));
  const zoomOut = () => setScale((s) => Math.max(0.5, s - 0.25));
  const resetZoom = () => setScale(1.0);

  const enterFullscreen = () => setIsFullscreen(true);
  const exitFullscreen = () => setIsFullscreen(false);

  const toolbar = (
    <div className="flex items-center justify-between px-4 py-2 border-b bg-card shrink-0">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <FileText className="h-4 w-4 text-red-400" />
        {title || "PDF Document"}
      </div>
      <div className="flex items-center gap-1">
        {/* Page navigation */}
        <Button
          variant="ghost"
          size="sm"
          onClick={goToPrevPage}
          disabled={pageNumber <= 1}
          className="h-8 w-8 p-0"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-xs text-muted-foreground min-w-[80px] text-center">
          {numPages > 0 ? `${pageNumber} / ${numPages}` : "Loading..."}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={goToNextPage}
          disabled={pageNumber >= numPages}
          className="h-8 w-8 p-0"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>

        <div className="w-px h-4 bg-border mx-1" />

        {/* Zoom controls */}
        <Button
          variant="ghost"
          size="sm"
          onClick={zoomOut}
          disabled={scale <= 0.5}
          className="h-8 w-8 p-0"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <button
          onClick={resetZoom}
          className="text-xs text-muted-foreground min-w-[48px] text-center hover:text-foreground transition-colors"
        >
          {Math.round(scale * 100)}%
        </button>
        <Button
          variant="ghost"
          size="sm"
          onClick={zoomIn}
          disabled={scale >= 3}
          className="h-8 w-8 p-0"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>

        <div className="w-px h-4 bg-border mx-1" />

        {/* Fullscreen */}
        <Button
          variant="ghost"
          size="sm"
          onClick={isFullscreen ? exitFullscreen : enterFullscreen}
          className="h-8 px-2"
        >
          {isFullscreen ? (
            <>
              <Minimize2 className="h-4 w-4 mr-1" />
              Exit
            </>
          ) : (
            <>
              <Maximize2 className="h-4 w-4 mr-1" />
              Fullscreen
            </>
          )}
        </Button>
      </div>
    </div>
  );

  const pdfContent = (
    <div
      className="overflow-auto flex justify-center bg-muted/30"
      style={{ height: isFullscreen ? "calc(100vh - 48px)" : "80vh" }}
    >
      {loadError ? (
        <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
          <FileText className="h-16 w-16 mb-4 opacity-50" />
          <p className="text-lg font-medium">Unable to load PDF</p>
          <p className="text-sm mt-1">{loadError}</p>
        </div>
      ) : !pdfData ? (
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
      <Document
        file={{ data: pdfData.slice(0) }}
        onLoadSuccess={onDocumentLoadSuccess}
        onLoadError={onDocumentLoadError}
        loading={
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        }
      >
        <Page
          pageNumber={pageNumber}
          scale={scale}
          renderTextLayer={true}
          renderAnnotationLayer={true}
        />
      </Document>
      )}
    </div>
  );

  return (
    <>
      {/* Fullscreen overlay */}
      {isFullscreen && (
        <div
          ref={fullscreenRef}
          className="fixed inset-0 z-50 bg-background flex flex-col"
        >
          {toolbar}
          {pdfContent}
        </div>
      )}

      {/* Inline card */}
      <Card className={cn(isFullscreen && "invisible")}>
        {toolbar}
        <CardContent className="p-0">{pdfContent}</CardContent>
      </Card>
    </>
  );
}
