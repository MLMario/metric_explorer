/**
 * Main routes for the frontend.
 */

import express from 'express';

const router = express.Router();

/**
 * Landing page - redirects to form or shows welcome
 */
router.get('/', (req, res) => {
  res.render('form', {
    title: 'New Investigation - Metric Drill-Down Agent',
    sessionId: null,
    files: [],
    errors: null,
  });
});

/**
 * Error page
 */
router.get('/error', (req, res) => {
  res.render('error', {
    title: 'Error',
    message: req.query.message || 'An error occurred',
    error: {},
  });
});

export default router;
