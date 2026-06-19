/**
 * shared/custom-form-fields — Controller-based form field wrappers.
 *
 * Every component follows the same contract:
 *   - `name`    — field path in the RHF form
 *   - `control` — form.control from useForm()
 *   - `label`   — visible label text
 *   - optional `description` rendered below the label
 *
 * Use these instead of raw <Input> + <Label> + form.register() so error
 * display, accessibility, and layout stay consistent across all forms.
 *
 * @module
 */
"use client";

import * as React from "react";
import {
  useController,
  type Control,
  type FieldValues,
  type Path,
} from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { FieldError } from "@/components/ui/field";
import { cn } from "@/lib/utils";

export { NativeSelectOption as FormSelectOption };

// ---------------------------------------------------------------------------
// FormInput
// ---------------------------------------------------------------------------

interface FormInputProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  description?: string;
  placeholder?: string;
  type?: React.HTMLInputTypeAttribute;
  disabled?: boolean;
  autoComplete?: string;
  autoFocus?: boolean;
  className?: string;
  /** Runs after the controller's own onChange — use for cross-field side effects (e.g. slug autofill). */
  onChangeSideEffect?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function FormInput<T extends FieldValues>({
  name,
  control,
  label,
  description,
  placeholder,
  type = "text",
  disabled,
  autoComplete,
  autoFocus,
  className,
  onChangeSideEffect,
}: FormInputProps<T>) {
  const { field, fieldState } = useController({ name, control });
  const id = String(name);

  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        aria-invalid={!!fieldState.error}
        value={field.value ?? ""}
        onChange={(e) => {
          field.onChange(e);
          onChangeSideEffect?.(e);
        }}
        onBlur={field.onBlur}
        ref={field.ref}
      />
      {fieldState.error && <FieldError errors={[fieldState.error]} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FormTextarea
// ---------------------------------------------------------------------------

interface FormTextareaProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
  className?: string;
}

export function FormTextarea<T extends FieldValues>({
  name,
  control,
  label,
  description,
  placeholder,
  disabled,
  rows,
  className,
}: FormTextareaProps<T>) {
  const { field, fieldState } = useController({ name, control });
  const id = String(name);

  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <Textarea
        id={id}
        placeholder={placeholder}
        disabled={disabled}
        rows={rows}
        aria-invalid={!!fieldState.error}
        value={field.value ?? ""}
        onChange={field.onChange}
        onBlur={field.onBlur}
        ref={field.ref}
      />
      {fieldState.error && <FieldError errors={[fieldState.error]} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FormSelect  (wraps NativeSelect)
// ---------------------------------------------------------------------------

interface FormSelectProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  description?: string;
  disabled?: boolean;
  className?: string;
  children: React.ReactNode;
}

export function FormSelect<T extends FieldValues>({
  name,
  control,
  label,
  description,
  disabled,
  className,
  children,
}: FormSelectProps<T>) {
  const { field, fieldState } = useController({ name, control });
  const id = String(name);

  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <NativeSelect
        id={id}
        disabled={disabled}
        aria-invalid={!!fieldState.error}
        value={field.value ?? ""}
        onChange={field.onChange}
        onBlur={field.onBlur}
        ref={field.ref}
        className="w-full"
      >
        {children}
      </NativeSelect>
      {fieldState.error && <FieldError errors={[fieldState.error]} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FormSwitch
// ---------------------------------------------------------------------------

interface FormSwitchProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export function FormSwitch<T extends FieldValues>({
  name,
  control,
  label,
  description,
  disabled,
  className,
}: FormSwitchProps<T>) {
  const { field, fieldState } = useController({ name, control });
  const id = String(name);

  return (
    <div className={cn("flex items-center justify-between gap-4", className)}>
      <div className="space-y-0.5">
        <Label htmlFor={id}>{label}</Label>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {fieldState.error && <FieldError errors={[fieldState.error]} />}
      </div>
      <Switch
        id={id}
        disabled={disabled}
        checked={!!field.value}
        onCheckedChange={field.onChange}
        ref={field.ref}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// FormCheckbox
// ---------------------------------------------------------------------------

interface FormCheckboxProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export function FormCheckbox<T extends FieldValues>({
  name,
  control,
  label,
  description,
  disabled,
  className,
}: FormCheckboxProps<T>) {
  const { field, fieldState } = useController({ name, control });
  const id = String(name);

  return (
    <div className={cn("flex items-start gap-3", className)}>
      <Checkbox
        id={id}
        disabled={disabled}
        checked={!!field.value}
        onCheckedChange={field.onChange}
        ref={field.ref}
        className="mt-0.5"
      />
      <div className="space-y-0.5">
        <Label htmlFor={id} className="font-normal cursor-pointer">
          {label}
        </Label>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {fieldState.error && <FieldError errors={[fieldState.error]} />}
      </div>
    </div>
  );
}
