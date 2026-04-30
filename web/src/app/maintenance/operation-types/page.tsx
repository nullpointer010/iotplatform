"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DeleteConfirm } from "@/components/delete-confirm";
import { OperationTypeForm } from "@/components/forms/operation-type-form";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";
import type { OperationType } from "@/lib/types";

export default function OperationTypesPage() {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<OperationType | null>(null);

  const list = useQuery({
    queryKey: ["operation-types"],
    queryFn: () => api.listOperationTypes(),
  });

  const del = useMutation({
    mutationFn: (id: string) => api.deleteOperationType(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operation-types"] });
      toast({ title: "Operation type removed" });
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : (err as Error).message;
      toast({ title: "Delete failed", description: message, variant: "destructive" });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Operation types</h1>
          <p className="text-sm text-muted-foreground">
            Maintenance operation catalog used by the maintenance log.
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> New
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New operation type</DialogTitle>
            </DialogHeader>
            <OperationTypeForm onDone={() => setCreateOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Catalog</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Component required</TableHead>
                <TableHead className="w-[1%]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    Loading…
                  </TableCell>
                </TableRow>
              )}
              {list.data?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    No operation types defined.
                  </TableCell>
                </TableRow>
              )}
              {list.data?.map((o) => (
                <TableRow key={o.id}>
                  <TableCell className="font-medium">{o.name}</TableCell>
                  <TableCell className="max-w-[32rem] truncate">
                    {o.description ?? "—"}
                  </TableCell>
                  <TableCell>
                    {o.requires_component ? (
                      <Badge variant="warning">required</Badge>
                    ) : (
                      <Badge variant="secondary">optional</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditing(o)}
                        aria-label="Edit"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <DeleteConfirm
                        title={`Delete "${o.name}"?`}
                        description="Operation types referenced by maintenance log entries cannot be deleted."
                        onConfirm={() => del.mutateAsync(o.id)}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label="Delete">
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        }
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit operation type</DialogTitle>
          </DialogHeader>
          {editing && (
            <OperationTypeForm
              initial={editing}
              onDone={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
