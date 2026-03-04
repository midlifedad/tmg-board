"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X, Calendar, Loader2, MapPin, Video, Link as LinkIcon } from "lucide-react";
import { meetingsApi } from "@/lib/api";

interface EditMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  meeting: {
    id: string;
    title: string;
    scheduled_date: string;
    duration_minutes?: number | null;
    location: string | null;
  } | null;
}

export function EditMeetingModal({ isOpen, onClose, onSuccess, meeting }: EditMeetingModalProps) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("10:00");
  const [duration, setDuration] = useState("60");
  const [locationType, setLocationType] = useState<"in-person" | "virtual">("in-person");
  const [location, setLocation] = useState("");
  const [meetingLink, setMeetingLink] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (meeting) {
      setTitle(meeting.title);
      // Extract date and time from the scheduled_date string directly
      // to avoid UTC conversion issues
      const parts = meeting.scheduled_date.split("T");
      setDate(parts[0]);
      setTime(parts[1]?.slice(0, 5) || "10:00");
      setDuration(String(meeting.duration_minutes || 60));

      // Determine location type from location string
      if (meeting.location?.startsWith("Virtual - ")) {
        setLocationType("virtual");
        setMeetingLink(meeting.location.replace("Virtual - ", ""));
        setLocation("");
      } else {
        setLocationType("in-person");
        setLocation(meeting.location || "");
        setMeetingLink("");
      }
    }
  }, [meeting]);

  const handleClose = () => {
    if (!submitting) {
      setError(null);
      onClose();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!meeting) return;

    if (!title.trim() || !date) {
      setError("Please provide a title and date");
      return;
    }

    if (locationType === "in-person" && !location.trim()) {
      setError("Please provide a location");
      return;
    }

    if (locationType === "virtual" && !meetingLink.trim()) {
      setError("Please provide a meeting link");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const scheduledDate = `${date}T${time}:00`;

      await meetingsApi.update(meeting.id, {
        title: title.trim(),
        scheduled_date: scheduledDate,
        duration_minutes: parseInt(duration) || 60,
        location: locationType === "virtual"
          ? `Virtual - ${meetingLink.trim()}`
          : location.trim(),
      });

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update meeting");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !meeting) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <Card className="relative z-10 w-full max-w-lg mx-4 shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Edit Meeting
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={handleClose} disabled={submitting}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Title */}
            <div>
              <label className="text-sm font-medium">Meeting Title *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Q1 Board Meeting"
                className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={submitting}
              />
            </div>

            {/* Date, Time, Duration */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium">Date *</label>
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  disabled={submitting}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Time *</label>
                <input
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  disabled={submitting}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Duration (min)</label>
                <input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  min="15"
                  step="15"
                  placeholder="60"
                  className="w-full mt-1 h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  disabled={submitting}
                />
              </div>
            </div>

            {/* Location Type */}
            <div>
              <label className="text-sm font-medium">Meeting Type *</label>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => setLocationType("in-person")}
                  className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-md border transition-colors ${
                    locationType === "in-person"
                      ? "border-primary bg-primary/5"
                      : "border-muted hover:border-muted-foreground/50"
                  }`}
                  disabled={submitting}
                >
                  <MapPin className="h-4 w-4" />
                  <span className="text-sm font-medium">In-Person</span>
                </button>
                <button
                  type="button"
                  onClick={() => setLocationType("virtual")}
                  className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-md border transition-colors ${
                    locationType === "virtual"
                      ? "border-primary bg-primary/5"
                      : "border-muted hover:border-muted-foreground/50"
                  }`}
                  disabled={submitting}
                >
                  <Video className="h-4 w-4" />
                  <span className="text-sm font-medium">Virtual</span>
                </button>
              </div>
            </div>

            {/* Location or Meeting Link */}
            {locationType === "in-person" ? (
              <div>
                <label className="text-sm font-medium">Location *</label>
                <div className="relative mt-1">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Conference Room A, 123 Main St"
                    className="w-full h-10 pl-10 pr-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    disabled={submitting}
                  />
                </div>
              </div>
            ) : (
              <div>
                <label className="text-sm font-medium">Meeting Link *</label>
                <div className="relative mt-1">
                  <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="url"
                    value={meetingLink}
                    onChange={(e) => setMeetingLink(e.target.value)}
                    placeholder="https://zoom.us/j/..."
                    className="w-full h-10 pl-10 pr-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    disabled={submitting}
                  />
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={handleClose} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !title.trim() || !date}>
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
