-- text_color.lua
function Span(el)
  local style = el.attributes['style']
  if not style then return el end

  local color_val = nil
  local bg_val = nil

  -- Loop through all CSS properties to prevent 'background-color' from matching 'color'
  for prop, hex in style:gmatch('([%a%-]+):%s*(#[%da-fA-F]+)') do
    if prop == 'color' then
      color_val = hex:sub(2):upper()
    elseif prop == 'background-color' then
      bg_val = hex:sub(2):upper()
    end
  end
  
  if not color_val and not bg_val then return el end

  -- For Raw LaTeX or PDF via LaTeX
  if FORMAT:match 'latex' or FORMAT:match 'beamer' then
    if bg_val then
      table.insert(el.content, 1, pandoc.RawInline('latex', '\\colorbox[HTML]{' .. bg_val .. '}{'))
      table.insert(el.content, pandoc.RawInline('latex', '}'))
    end
    if color_val then
      table.insert(el.content, 1, pandoc.RawInline('latex', '\\textcolor[HTML]{' .. color_val .. '}{'))
      table.insert(el.content, pandoc.RawInline('latex', '}'))
    end
    return el

  -- For Typst (Raw .typ or PDF via Typst)
  elseif FORMAT:match 'typst' then
    if color_val then
      table.insert(el.content, 1, pandoc.RawInline('typst', '#text(fill: rgb("#' .. color_val .. '"))['))
      table.insert(el.content, pandoc.RawInline('typst', ']'))
    end
    if bg_val then
      table.insert(el.content, 1, pandoc.RawInline('typst', '#highlight(fill: rgb("#' .. bg_val .. '"))['))
      table.insert(el.content, pandoc.RawInline('typst', ']'))
    end
    return el

  -- For Word (DOCX)
  elseif FORMAT:match 'docx' then
    local styleName = ""
    
    if color_val then styleName = styleName .. "Color" .. color_val end
    if bg_val then styleName = styleName .. "Bg" .. bg_val end
    
    el.attributes['custom-style'] = styleName
    -- We can safely remove the style attribute for DOCX so it doesn't cause bloat
    el.attributes['style'] = nil 
    return el
  end
end