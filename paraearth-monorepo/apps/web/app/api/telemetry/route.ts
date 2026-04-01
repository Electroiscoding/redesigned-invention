import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  // AQC frame-time logging
  return NextResponse.json({ success: true });
}