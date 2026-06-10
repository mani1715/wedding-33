import React from 'react';
import { motion } from 'framer-motion';

/**
 * ScrollSection — cinematic scroll-triggered reveal wrapper.
 * Usage: <ScrollSection><h1>Hello</h1></ScrollSection>
 */
const ScrollSection = ({
  children,
  delay = 0,
  amount = 0.25,
  className = '',
  as = 'section',
  testid,
}) => {
  const MotionTag = motion[as] || motion.section;
  return (
    <MotionTag
      initial={{ opacity: 0, y: 40, filter: 'blur(6px)' }}
      whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      viewport={{ once: true, amount }}
      transition={{ duration: 1.0, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
      data-testid={testid}
    >
      {children}
    </MotionTag>
  );
};

export default ScrollSection;
