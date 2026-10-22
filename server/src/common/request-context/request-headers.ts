import type { IncomingHttpHeaders } from 'node:http';
import { isIPv4, isIPv6 } from 'node:net';
import { HttpStatus } from '@nestjs/common';
import { isUUID } from 'class-validator';
import { OPEN_BANKING_HEADER } from '../open-banking-headers.js';
import {
  PROBLEM_CODE,
  ProblemDetailsException,
  createProblem,
} from '../problem-details/problem-details.js';

export const PSU_ID_PATTERN = /^[A-Za-z0-9-]{1,64}$/;

export function readConsentIdHeader(headers: IncomingHttpHeaders): string {
  const consentId = readSingleHeader(headers, OPEN_BANKING_HEADER.CONSENT_ID);
  if (consentId === undefined || !isUUID(consentId)) {
    throw createFormatError('Consent-ID header must be a UUID');
  }
  return consentId;
}

export function readPsuIdHeader(
  headers: IncomingHttpHeaders,
): string | undefined {
  const psuId = readSingleHeader(headers, OPEN_BANKING_HEADER.PSU_ID);
  if (psuId !== undefined && !PSU_ID_PATTERN.test(psuId)) {
    throw createFormatError(
      'PSU-ID header must be 1 to 64 letters, digits or hyphens',
    );
  }
  return psuId;
}

export function readPsuIpAddress(
  headers: IncomingHttpHeaders,
  requestIp: string | undefined,
): string | undefined {
  const psuIpAddress = readSingleHeader(
    headers,
    OPEN_BANKING_HEADER.PSU_IP_ADDRESS,
  );
  if (psuIpAddress === undefined) {
    return requestIp !== undefined && isIpAddress(requestIp)
      ? requestIp
      : undefined;
  }
  if (!isIpAddress(psuIpAddress)) {
    throw createFormatError(
      'PSU-IP-Address header must be an IPv4 or IPv6 address',
    );
  }
  return psuIpAddress;
}

// Node lowercases incoming header names.
function readSingleHeader(
  headers: IncomingHttpHeaders,
  headerName: string,
): string | undefined {
  const value = headers[headerName.toLowerCase()];
  return typeof value === 'string' ? value : undefined;
}

function isIpAddress(value: string): boolean {
  return isIPv4(value) || isIPv6(value);
}

function createFormatError(detail: string): ProblemDetailsException {
  return new ProblemDetailsException(
    createProblem({
      status: HttpStatus.BAD_REQUEST,
      code: PROBLEM_CODE.FORMAT_ERROR,
      detail,
    }),
  );
}
