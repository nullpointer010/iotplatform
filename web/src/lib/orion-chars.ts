export const ORION_FORBIDDEN = /[<>"'=;()]/;

export const ORION_FORBIDDEN_HUMAN = "< > \" ' = ; ( )";

export function findForbiddenChar(value: string): string | null {
  const match = ORION_FORBIDDEN.exec(value);
  return match ? match[0] : null;
}
