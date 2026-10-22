import { HttpStatus } from '@nestjs/common';
import { plainToInstance, type ClassConstructor } from 'class-transformer';
import { validateSync, type ValidationError } from 'class-validator';
import {
  PROBLEM_CODE,
  ProblemDetailsException,
  createProblem,
} from '../common/problem-details/problem-details.js';

export function parseUpstreamPayload<T extends object>(
  dtoClass: ClassConstructor<T>,
  body: unknown,
  operationName: string,
): T {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    throw createContractViolation(operationName, 'body is not a JSON object');
  }
  const payload = plainToInstance(dtoClass, body);
  const [firstError] = validateSync(payload, { whitelist: true });
  if (firstError !== undefined) {
    throw createContractViolation(
      operationName,
      describeFirstIssue(firstError),
    );
  }
  return payload;
}

function describeFirstIssue(
  error: ValidationError,
  parentPath?: string,
): string {
  const propertyPath =
    parentPath === undefined
      ? error.property
      : `${parentPath}.${error.property}`;
  const [firstConstraint] = Object.values(error.constraints ?? {});
  if (firstConstraint !== undefined) {
    return `${propertyPath}: ${firstConstraint}`;
  }
  const [firstChild] = error.children ?? [];
  return firstChild === undefined
    ? `${propertyPath} is invalid`
    : describeFirstIssue(firstChild, propertyPath);
}

function createContractViolation(
  operationName: string,
  issue: string,
): ProblemDetailsException {
  return new ProblemDetailsException(
    createProblem({
      status: HttpStatus.BAD_GATEWAY,
      code: PROBLEM_CODE.UPSTREAM_CONTRACT_VIOLATION,
      detail: `TBC sandbox response to ${operationName} does not match the specification: ${issue}`,
    }),
  );
}
